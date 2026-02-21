import fitz
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from config import CHUNK_SIZE, CHUNK_OVERLAP

def process_pdf(file_path: str, filename: str) -> List[Document]:
    doc = fitz.open(file_path)
    full_text = ""
    page_map = []
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            full_text += text + "\n"
            page_map.extend([page_num] * len(text.split()))
    
    doc.close()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
    )
    
    chunks = text_splitter.split_text(full_text)
    documents = []
    
    for i, chunk in enumerate(chunks):
        words = chunk.split()
        if words:
            avg_page = page_map[min(len(page_map) - 1, len(words) // 2)] if page_map else 1
        else:
            avg_page = 1
        
        documents.append(
            Document(
                page_content=chunk,
                metadata={"source": filename, "page": avg_page}
            )
        )
    
    return documents
