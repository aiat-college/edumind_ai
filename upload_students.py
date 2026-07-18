import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Read CSV
df = pd.read_csv("StudentPerformanceFactors.csv")

print(f"Found {len(df)} students in CSV")

sections = ["A", "B", "C", "D"]
classes = ["8th", "9th", "10th", "11th", "12th"]

for index, row in df.iterrows():

    percentage = float(row["Exam_Score"])
    attendance = float(row["Attendance"])

    student = {
        "name": f"Student_{index + 1}",
        "roll_no": str(1000 + index),
        "class": classes[index % len(classes)],
        "section": sections[index % len(sections)],
        "group": "General",
        "attendance_percent": round(attendance, 2),
        "marks_total": round((percentage / 100) * 500),
        "max_marks": 500,
        "percentage": round(percentage, 2)
    }

    db.collection("students").add(student)

    if (index + 1) % 100 == 0:
        print(f"Uploaded {index + 1} students...")

print("\n✅ All students uploaded successfully!")