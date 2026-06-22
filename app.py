"""
SCHOOL RAG CHATBOT - WEBSITE VERSION (Groq LLM + Gemini Embedding)

Run panna:
    1. pip install -r requirements.txt --break-system-packages
    2. pip install llama-index-llms-groq --break-system-packages
    3. export GOOGLE_API_KEY="unga-gemini-key"
    4. export GROQ_API_KEY="unga-groq-key"
    5. python3 app.py
    6. Browser-la: http://localhost:8000 thirakkalam
"""

import os
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from llama_index.core import (
    VectorStoreIndex,
    Document,
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms.groq import Groq
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

STORAGE_DIR = "./storage"
GROUP_SIZE = 20

# ---------------------------------------------------------------
# STEP 1: LLM = Groq, Embedding = Gemini
# ---------------------------------------------------------------
gemini_api_key = os.environ.get("GOOGLE_API_KEY")
if not gemini_api_key:
    raise ValueError(
        "GOOGLE_API_KEY set pannala! Terminal-la idha type pannunga:\n"
        'export GOOGLE_API_KEY="unga-key-inga"'
    )

groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY set pannala! Terminal-la idha type pannunga:\n"
        'export GROQ_API_KEY="unga-key-inga"'
    )

Settings.llm = Groq(
    model="llama-3.3-70b-versatile",
    api_key=groq_api_key,
    context_window=128000,
    system_prompt=(
        "You are a helpful school records assistant. Always respond in clear, "
        "simple English only, regardless of what language the question is "
        "asked in. Give ONLY the direct, final answer to the question. "
        "Do not explain your reasoning, do not mention names that were "
        "excluded or why, and do not show your thought process. "
        "For example, if asked for the names of boys in a class, reply with "
        "just the list of boys' names — nothing about which students are "
        "girls or were excluded. If asked for girls, give only girls' names. "
        "Keep answers short, direct, and to the point."
    ),
)
Settings.embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-001", api_key=gemini_api_key)

# ---------------------------------------------------------------
# STEP 2: Firebase connect pannunga
# ---------------------------------------------------------------
print("Connecting to Firebase...")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def fetch_students_from_firebase():
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
        chunk = student_texts[i : i + GROUP_SIZE]
        combined_text = "\n".join(chunk)
        documents.append(Document(text=combined_text))

    return documents, len(student_texts)


# ---------------------------------------------------------------
# STEP 3: Index build / load pannunga
# ---------------------------------------------------------------
if os.path.exists(STORAGE_DIR):
    print("Saved index irukku -- load panren (fast)...")
    storage_context = StorageContext.from_defaults(persist_dir=STORAGE_DIR)
    index = load_index_from_storage(storage_context)
else:
    print("Fetching students from Firebase...")
    documents, total_students = fetch_students_from_firebase()
    print(f"Fetched {total_students} students, {len(documents)} groups-a serthen")

    print("Building search index...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)

    print("Index-a save panren...")
    index.storage_context.persist(persist_dir=STORAGE_DIR)

query_engine = index.as_query_engine(
    similarity_top_k=4,
    response_mode="tree_summarize",
)
print("Ready! Server start aagudhu...")


# ---------------------------------------------------------------
# STEP 4: FastAPI app - /chat API + frontend serve pannunga
# ---------------------------------------------------------------
app = FastAPI(title="School RAG Chatbot")


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


# ---------------------------------------------------------------
# CHAT HISTORY - stored in Firestore "chat_sessions" collection
# ---------------------------------------------------------------
@app.post("/sessions")
def create_session():
    doc_ref = db.collection("chat_sessions").document()
    doc_ref.set({
        "title": "New chat",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "messages": [],
    })
    return {"session_id": doc_ref.id}


@app.get("/sessions")
def list_sessions():
    docs = db.collection("chat_sessions").order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).stream()
    sessions = []
    for doc in docs:
        data = doc.to_dict()
        sessions.append({
            "session_id": doc.id,
            "title": data.get("title", "New chat"),
        })
    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    doc = db.collection("chat_sessions").document(session_id).get()
    if not doc.exists:
        return {"messages": []}
    return {"messages": doc.to_dict().get("messages", [])}


@app.post("/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        return {"answer": "Please type a question."}
    try:
        response = query_engine.query(question)
        answer = str(response)
    except Exception as e:
        answer = f"Something went wrong: {e}"

    if req.session_id:
        doc_ref = db.collection("chat_sessions").document(req.session_id)
        doc = doc_ref.get()
        existing = doc.to_dict() if doc.exists else {"messages": [], "title": "New chat"}
        messages = existing.get("messages", [])
        messages.append({"role": "user", "text": question})
        messages.append({"role": "bot", "text": answer})

        update_data = {"messages": messages}
        if existing.get("title", "New chat") == "New chat" and len(messages) <= 2:
            update_data["title"] = question[:40] + ("..." if len(question) > 40 else "")

        doc_ref.set(update_data, merge=True)

    return {"answer": answer}


@app.get("/")
def serve_home():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)