"""
EDUMIND AI — BACKEND (app.py)
Firebase + LlamaIndex + Groq + Gemini Embedding

This file handles:
1. Firebase connection — fetch student data
2. LlamaIndex — build/load search index
3. Groq LLM — generate answers (14400 requests/day FREE)
4. System prompt — LLM behavior instructions

This is BACKEND only — no UI here.
gradio_ui.py imports this file for the frontend.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from llama_index.core import (
    VectorStoreIndex,
    Document,
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms.groq import Groq
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# ---------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------
STORAGE_DIR = "./storage"
GROUP_SIZE = 20

# ---------------------------------------------------------------
# STEP 1: API Keys
# ---------------------------------------------------------------
google_api_key = os.environ.get("GOOGLE_API_KEY")
groq_api_key = os.environ.get("GROQ_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY is not set! Run: export GOOGLE_API_KEY='your-key'")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set! Run: export GROQ_API_KEY='your-key'")

# ---------------------------------------------------------------
# STEP 2: System Prompt — LLM behaviour instructions
# ---------------------------------------------------------------
SYSTEM_PROMPT = """You are EduMind AI, an intelligent school data assistant.
You ONLY answer questions based on the student data provided in the context.

Rules you must follow:
1. Only use information from the provided student data context
2. If asked for a list of students, format it as a clear numbered list
3. If the information is not available in the data, say exactly:
   "This information is not available in the database."
4. Never guess, assume, or make up any student information
5. Always be helpful, clear, and professional
6. When giving student details, include: Name, Roll No, Class, Section, Marks, Percentage
7. If asked about a specific student, give all available details about them"""

# ---------------------------------------------------------------
# STEP 3: Configure LLM + Embedding
# ---------------------------------------------------------------
# Groq — fast, free (14400 requests/day), answer generate panna
Settings.llm = Groq(
    model="llama-3.1-8b-instant",
    api_key=groq_api_key,
    system_prompt=SYSTEM_PROMPT,
)

# Gemini Embedding — text to vectors (used only once when building index)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=google_api_key
)

# ---------------------------------------------------------------
# STEP 4: Firebase Connection
# ---------------------------------------------------------------
print("[Backend] Connecting to Firebase...")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
print("[Backend] Firebase connected!")

# ---------------------------------------------------------------
# STEP 5: Fetch Students from Firestore
# ---------------------------------------------------------------
def fetch_students_from_firebase():
    """
    Reads all students from Firestore 'students' collection.
    Groups 20 students into one document (to reduce embedding API calls).
    """
    students_ref = db.collection("students").stream()
    student_texts = []

    for doc in students_ref:
        data = doc.to_dict()
        text = (
            f"Student Name: {data.get('name', 'N/A')}, "
            f"Roll No: {data.get('roll_no', 'N/A')}, "
            f"Class: {data.get('class', 'N/A')}, "
            f"Section: {data.get('section', 'N/A')}, "
            f"Group: {data.get('group', 'N/A')}, "
            f"Marks: {data.get('marks_total', 'N/A')}/{data.get('max_marks', 'N/A')}, "
            f"Percentage: {data.get('percentage', 'N/A')}%, "
            f"Attendance: {data.get('attendance_percent', 'N/A')}%"
        )
        student_texts.append(text)

    documents = []
    for i in range(0, len(student_texts), GROUP_SIZE):
        chunk = student_texts[i: i + GROUP_SIZE]
        documents.append(Document(text="\n".join(chunk)))

    return documents, len(student_texts)

# ---------------------------------------------------------------
# STEP 6: Build or Load LlamaIndex
# ---------------------------------------------------------------
if os.path.exists(STORAGE_DIR):
    print("[Backend] Loading saved index...")
    storage_context = StorageContext.from_defaults(persist_dir=STORAGE_DIR)
    index = load_index_from_storage(storage_context)
    print("[Backend] Index loaded!")
else:
    print("[Backend] Fetching students from Firebase...")
    documents, total = fetch_students_from_firebase()
    print(f"[Backend] Fetched {total} students")
    print("[Backend] Building index...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)
    index.storage_context.persist(persist_dir=STORAGE_DIR)
    print("[Backend] Index saved!")

query_engine = index.as_query_engine(similarity_top_k=3)
print("[Backend] Ready to answer questions!")

# ---------------------------------------------------------------
# STEP 7: Get Answer Function (called by frontend)
# ---------------------------------------------------------------
def get_answer(question: str) -> str:
    """
    Takes a question string.
    Returns an answer string.
    This function is called by gradio_ui.py (frontend).
    System prompt is automatically applied by LlamaIndex via Settings.llm.
    """
    if not question.strip():
        return "Please type a question!"

    try:
        response = query_engine.query(question)
        return str(response)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate_limit" in error_msg.lower():
            return "Rate limit reached. Please wait a moment and try again."
        return f"Error: {error_msg}"