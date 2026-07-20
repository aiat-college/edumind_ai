import os

from llama_index.core import (
    Settings,
    StorageContext,
    load_index_from_storage,
)

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq

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

    if not os.path.exists(STORAGE_DIR):
        raise FileNotFoundError(
            "Storage folder not found. Please upload the storage folder."
        )

    print("Loading existing index...")

    storage_context = StorageContext.from_defaults(
        persist_dir=STORAGE_DIR
    )

    index = load_index_from_storage(storage_context)

    print("Index loaded successfully.")

    return index.as_query_engine(similarity_top_k=3)