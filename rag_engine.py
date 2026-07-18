import os

from llama_index.core import (
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
    Document,
)

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq

from firestore_utils import db

STORAGE_DIR = "./storage"


SYSTEM_PROMPT = """
You are EduMind AI.

Answer ONLY using the retrieved student information.

Rules:

1. Never guess.
2. Never create fake information.
3. If the information is unavailable say:
"This information is not available in the database."
4. Keep answers short and professional.
"""


def build_index():

    print("Loading students from Firestore...")

    documents = []

    docs = db.collection("students").stream()

    for doc in docs:

        student = doc.to_dict()

        text = f"""
Name: {student.get('name','')}
Roll Number: {student.get('roll_no','')}
Class: {student.get('class','')}
Section: {student.get('section','')}
Group: {student.get('group','')}
Marks: {student.get('marks_total','')}
Maximum Marks: {student.get('max_marks','')}
Percentage: {student.get('percentage','')}
Attendance: {student.get('attendance_percent','')}
"""

        documents.append(Document(text=text))

    print(f"Loaded {len(documents)} students.")

    index = VectorStoreIndex.from_documents(documents)

    index.storage_context.persist(STORAGE_DIR)

    print("Index created successfully.")

    return index


def load_rag_engine():

    groq_api_key = os.environ.get("GROQ_API_KEY")

    if not groq_api_key:
        raise ValueError("Please set GROQ_API_KEY environment variable.")

    Settings.llm = Groq(
        model="llama-3.1-8b-instant",
        api_key=groq_api_key,
        system_prompt=SYSTEM_PROMPT,
    )

    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if os.path.exists(STORAGE_DIR):

        print("Loading existing index...")

        storage_context = StorageContext.from_defaults(
            persist_dir=STORAGE_DIR
        )

        index = load_index_from_storage(storage_context)

    else:

        print("Storage folder not found.")
        print("Building index...")

        index = build_index()

    return index.as_query_engine(similarity_top_k=10)