import pickle
import os
import numpy as np
import faiss
from langchain_core.documents import Document
from typing import List, Optional
from config import VECTOR_DB_DIR, COLLECTION_NAME

class VectorStore:
    def __init__(self, persist_directory: str = VECTOR_DB_DIR, collection_name: str = COLLECTION_NAME):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.index_file = os.path.join(persist_directory, f"{collection_name}.index")
        self.docs_file = os.path.join(persist_directory, f"{collection_name}.docs")
        self.index: Optional[faiss.Index] = None
        self.documents: List[Document] = []
        self._load_or_create_index()

    def _load_or_create_index(self):
        os.makedirs(self.persist_directory, exist_ok=True)
        
        if os.path.exists(self.index_file) and os.path.exists(self.docs_file):
            self._load_index()
        else:
            embedding_dim = 384
            self.index = faiss.IndexFlatL2(embedding_dim)
            self.documents = []

    def _load_index(self):
        self.index = faiss.read_index(self.index_file)
        with open(self.docs_file, 'rb') as f:
            self.documents = pickle.load(f)

    def _save_index(self):
        faiss.write_index(self.index, self.index_file)
        with open(self.docs_file, 'wb') as f:
            pickle.dump(self.documents, f)

    def add_documents(self, docs: List[Document], embeddings: List[List[float]]):
        if not self.index:
            embedding_dim = len(embeddings[0])
            self.index = faiss.IndexFlatL2(embedding_dim)
        
        embeddings_array = np.array(embeddings, dtype=np.float32)
        self.index.add(embeddings_array)
        self.documents.extend(docs)
        self._save_index()

    def similarity_search(self, query_embedding: List[float], k: int = 5) -> List[Document]:
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_array = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query_array, k)
        
        documents = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx < len(self.documents):
                documents.append(self.documents[idx])
        
        return documents

    def clear(self):
        embedding_dim = 384
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.documents = []
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
        if os.path.exists(self.docs_file):
            os.remove(self.docs_file)

    def remove_documents_by_source(self, source: str):
        self.documents = [doc for doc in self.documents if doc.metadata.get('source') != source]
        self._save_index()

_vector_store = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
