import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# ---------------------------------------------------
# Firebase Initialization
# ---------------------------------------------------

firebase_credentials = os.environ.get("FIREBASE_CREDENTIALS")

if not firebase_admin._apps:

    if firebase_credentials:
        cred = credentials.Certificate(json.loads(firebase_credentials))
    else:
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------------------------
# Total Students
# ---------------------------------------------------

def get_total_students():
    docs = list(db.collection("students").stream())
    return len(docs)

# ---------------------------------------------------
# Search by Roll Number
# ---------------------------------------------------

def get_student_by_roll(roll_no):

    docs = (
        db.collection("students")
        .where("roll_no", "==", str(roll_no))
        .stream()
    )

    return [doc.to_dict() for doc in docs]

# ---------------------------------------------------
# Search by Name
# ---------------------------------------------------

def get_student_by_name(name):

    result = []

    docs = db.collection("students").stream()

    for doc in docs:

        data = doc.to_dict()

        if name.lower() in data.get("name", "").lower():
            result.append(data)

    return result

# ---------------------------------------------------
# Search by Class
# ---------------------------------------------------

def get_students_by_class(class_name):

    docs = (
        db.collection("students")
        .where("class", "==", class_name)
        .stream()
    )

    return [doc.to_dict() for doc in docs]

# ---------------------------------------------------
# Search by Section
# ---------------------------------------------------

def get_students_by_section(section):

    docs = (
        db.collection("students")
        .where("section", "==", section)
        .stream()
    )

    return [doc.to_dict() for doc in docs]

# ---------------------------------------------------
# Search by Group
# ---------------------------------------------------

def get_students_by_group(group_name):

    docs = db.collection("students").stream()

    students = []

    for doc in docs:

        data = doc.to_dict()

        if group_name.lower() in data.get("group", "").lower():
            students.append(data)

    return students

# ---------------------------------------------------
# Top Students
# ---------------------------------------------------

def get_top_students(limit=10):

    docs = db.collection("students").stream()

    students = [doc.to_dict() for doc in docs]

    students.sort(
        key=lambda x: float(x.get("percentage", 0)),
        reverse=True,
    )

    return students[:limit]

# ---------------------------------------------------
# Highest Percentage Student(s)
# ---------------------------------------------------

def get_highest_percentage():

    docs = db.collection("students").stream()

    students = [doc.to_dict() for doc in docs]

    if not students:
        return []

    highest = max(
        float(student.get("percentage", 0))
        for student in students
    )

    return [
        student
        for student in students
        if float(student.get("percentage", 0)) == highest
    ]

# ---------------------------------------------------
# Students Below Attendance
# ---------------------------------------------------

def get_students_below_attendance(limit):

    docs = db.collection("students").stream()

    students = []

    for doc in docs:

        data = doc.to_dict()

        try:
            attendance = float(data.get("attendance_percent", 0))

            if attendance < limit:
                students.append(data)

        except (ValueError, TypeError):
            continue

    students.sort(
        key=lambda x: float(x.get("attendance_percent", 0))
    )

    return students