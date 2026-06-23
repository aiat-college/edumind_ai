"""
SCHOOL RAG CHATBOT - WEBSITE VERSION (Groq LLM + Gemini Embedding)

To run:
    1. pip install -r requirements.txt --break-system-packages
    2. pip install llama-index-llms-groq --break-system-packages
    3. export GOOGLE_API_KEY="your-gemini-key"
    4. export GROQ_API_KEY="your-groq-key"
    5. python3 app.py
    6. Open in browser: http://localhost:8000
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
# STEP 1: Set up LLM = Groq, Embedding model = Gemini
# ---------------------------------------------------------------
gemini_api_key = os.environ.get("GOOGLE_API_KEY")
if not gemini_api_key:
    raise ValueError(
        "GOOGLE_API_KEY is not set! Run this in your terminal:\n"
        'export GOOGLE_API_KEY="your-key-here"'
    )

groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY is not set! Run this in your terminal:\n"
        'export GROQ_API_KEY="your-key-here"'
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
# STEP 2: Connect to Firebase
# ---------------------------------------------------------------
print("Connecting to Firebase...")
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def fetch_students_from_firebase():
    """Fetch all student records from Firestore and group them into chunks."""
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

    # Group every 20 students into one document, to reduce the number
    # of embedding API calls (avoids hitting rate limits)
    documents = []
    for i in range(0, len(student_texts), GROUP_SIZE):
        chunk = student_texts[i : i + GROUP_SIZE]
        combined_text = "\n".join(chunk)
        documents.append(Document(text=combined_text))

    return documents, len(student_texts)


# ---------------------------------------------------------------
# STEP 3: Build or load the vector index
# (built once on first run, then loaded from disk afterwards)
# ---------------------------------------------------------------
if os.path.exists(STORAGE_DIR):
    print("Saved index found -- loading it (fast)...")
    storage_context = StorageContext.from_defaults(persist_dir=STORAGE_DIR)
    index = load_index_from_storage(storage_context)
else:
    print("Fetching students from Firebase...")
    documents, total_students = fetch_students_from_firebase()
    print(f"Fetched {total_students} students, grouped into {len(documents)} chunks")

    print("Building search index...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)

    print("Saving index to disk...")
    index.storage_context.persist(persist_dir=STORAGE_DIR)

query_engine = index.as_query_engine(
    similarity_top_k=4,
    response_mode="tree_summarize",
)
print("Ready! Starting server...")


# ---------------------------------------------------------------
# STEP 4: FastAPI app - /chat API + frontend serving
# ---------------------------------------------------------------
app = FastAPI(title="School RAG Chatbot")


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


# ---------------------------------------------------------------
# CHAT HISTORY - stored in the Firestore "chat_sessions" collection
# ---------------------------------------------------------------
@app.post("/sessions")
def create_session():
    """Create a new chat session, shown as a new entry in the sidebar."""
    doc_ref = db.collection("chat_sessions").document()
    doc_ref.set({
        "title": "New chat",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "messages": [],
    })
    return {"session_id": doc_ref.id}


@app.get("/sessions")
def list_sessions():
    """List all past chat sessions for the sidebar, latest first."""
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
    """Return the full message history for one specific chat session."""
    doc = db.collection("chat_sessions").document(session_id).get()
    if not doc.exists:
        return {"messages": []}
    return {"messages": doc.to_dict().get("messages", [])}


def _save_to_history(session_id, question, answer):
    """Save a question + answer pair into the session's message history."""
    doc_ref = db.collection("chat_sessions").document(session_id)
    doc = doc_ref.get()
    existing = doc.to_dict() if doc.exists else {"messages": [], "title": "New chat"}
    messages = existing.get("messages", [])
    messages.append({"role": "user", "text": question})
    messages.append({"role": "bot", "text": answer})

    update_data = {"messages": messages}
    # Use the first question as the session title (shown in the sidebar)
    if existing.get("title", "New chat") == "New chat" and len(messages) <= 2:
        update_data["title"] = question[:40] + ("..." if len(question) > 40 else "")

    doc_ref.set(update_data, merge=True)


@app.post("/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        return {"answer": "Please type a question."}

    question_lower = question.lower()

    # ---------------------------------------------------------------
    # For counting questions ("how many students", "total students"),
    # we do NOT use RAG / semantic search. RAG only looks at the top
    # few similar chunks, so it cannot give an accurate total count.
    # Instead, we query Firestore directly for the exact, correct count.
    # ---------------------------------------------------------------
    if ("how many" in question_lower or "total" in question_lower) and "student" in question_lower:
        try:
            all_docs = list(db.collection("students").stream())
            total_count = len(all_docs)

            class_filter = None
            for grade in ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th",
                          "9th", "10th", "11th", "12th"]:
                if grade in question_lower:
                    class_filter = grade
                    break

            if class_filter:
                matching = [
                    d for d in all_docs
                    if str(d.to_dict().get("class", "")).lower().startswith(class_filter[:-2])
                ]
                answer = f"There are {len(matching)} students in {class_filter} standard."
            else:
                answer = f"There are {total_count} students in total in the school."

        except Exception as e:
            answer = f"Something went wrong: {e}"

        if req.session_id:
            _save_to_history(req.session_id, question, answer)
        return {"answer": answer}

    # ---------------------------------------------------------------
    # For all other questions (names, marks, percentage, attendance),
    # use the RAG query engine as usual
    # ---------------------------------------------------------------
    try:
        response = query_engine.query(question)
        answer = str(response)
    except Exception as e:
        answer = f"Something went wrong: {e}"

    if req.session_id:
        _save_to_history(req.session_id, question, answer)

    return {"answer": answer}


@app.get("/")
def serve_home():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)