import os
import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

class RAGService:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)
        self.documents = []

    def add_pdf_to_index(self, pdf_path):
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content: text += content
        
        chunks = [text[i:i+800] for i in range(0, len(text), 800)]
        self.documents.extend(chunks)
        embeddings = self.embedder.encode(chunks)
        self.index.add(np.array(embeddings).astype('float32'))

    def query_manuals(self, query, k=2):
        if not self.documents: return "No manual data found."
        query_vec = self.embedder.encode([query])
        _, indices = self.index.search(np.array(query_vec).astype('float32'), k)
        return "\n".join([self.documents[i] for i in indices[0]])

rag = RAGService()