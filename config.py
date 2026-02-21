import os
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = "uploads"
VECTOR_DB_DIR = "vector_db"
COLLECTION_NAME = "academic_papers"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
