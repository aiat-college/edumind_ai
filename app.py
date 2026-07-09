"""
EDUMIND AI — BACKEND (app.py)
Firebase + LlamaIndex + Groq

This file handles:
1. Firebase connection — fetch student data
2. LlamaIndex — build/load search index
3. Groq LLM — generate answers

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
from llama_index.llms.google_genai import GoogleGenAI
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
# STEP 2: Configure LLM + Embedding
# ---------------------------------------------------------------
# Groq — answer generate panna (14400 requests/day free)
Settings.llm = GoogleGenAI(model="gemini-2.5-flash-lite", api_key=google_api_key)

# Gemini — text to vectors (embedding only, used once)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=google_api_key
)

# ---------------------------------------------------------------
# STEP 3: Firebase Connection
# ---------------------------------------------------------------
print("[Backend] Connecting to Firebase...")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
print("[Backend] Firebase connected!")

# ---------------------------------------------------------------
# STEP 4: Fetch Students from Firestore
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
# STEP 5: Build or Load LlamaIndex
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

query_engine = index.as_query_engine(similarity_top_k=10)
print("[Backend] Ready to answer questions!")

# ---------------------------------------------------------------
# STEP 6: Get Answer Function (called by frontend)
# ---------------------------------------------------------------
def get_answer(question: str) -> str:
    """
    Takes a question string.
    Returns an answer string.
    This function is called by gradio_ui.py (frontend).
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
 