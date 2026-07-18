from firestore_utils import (
    get_total_students,
    get_student_by_name,
    get_student_by_roll,
    get_students_by_class,
    get_students_by_section,
    get_top_students,
)

from rag_engine import load_rag_engine

query_engine = load_rag_engine()


def format_students(students):

    if not students:
        return "No matching students found."

    result = ""

    for i, s in enumerate(students, 1):

        result += (
            f"{i}. {s['name']}\n"
            f"Roll No : {s['roll_no']}\n"
            f"Class : {s['class']}\n"
            f"Section : {s['section']}\n"
            f"Percentage : {s['percentage']}%\n"
            f"Attendance : {s['attendance_percent']}%\n\n"
        )

    return result


def get_answer(question):

    q = question.lower().strip()

    try:

        # ------------------------------
        # TOTAL STUDENTS
        # ------------------------------
        if (
            "how many students" in q
            or "total students" in q
            or "student count" in q
        ):

            total = get_total_students()

            return f"There are {total} students in the database."

        # ------------------------------
        # TOP STUDENTS
        # ------------------------------
        if "top" in q and "student" in q:

            students = get_top_students()

            return format_students(students)

        # ------------------------------
        # SEARCH BY ROLL NUMBER
        # ------------------------------
        if "roll" in q:

            words = q.split()

            roll = None

            for w in words:
                if w.isdigit():
                    roll = w
                    break

            if roll:

                students = get_student_by_roll(roll)

                return format_students(students)

        # ------------------------------
        # CLASS SEARCH
        # ------------------------------
        if "class" in q:

            words = question.split()

            for word in words:

                if (
                    word.endswith("th")
                    or word.endswith("st")
                    or word.endswith("nd")
                ):

                    students = get_students_by_class(word)

                    return format_students(students)

        # ------------------------------
        # SECTION SEARCH
        # ------------------------------
        if "section" in q:

            words = question.split()

            for word in words:

                if word.upper() in ["A", "B", "C", "D"]:

                    students = get_students_by_section(word.upper())

                    return format_students(students)

        # ------------------------------
        # NAME SEARCH
        # ------------------------------
        if "student" in q:

            words = question.split()

            name = words[-1]

            students = get_student_by_name(name)

            if students:

                return format_students(students)

        # ------------------------------
        # AI SEARCH
        # ------------------------------
        response = query_engine.query(question)

        return str(response)

    except Exception as e:

        return f"Error : {e}"