import os
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
import chromadb

# Path to documents folder
DOCS_PATH = "documents/"

def load_pdfs():
    texts = []
    for file_name in os.listdir(DOCS_PATH):
        if file_name.endswith(".pdf"):
            path = os.path.join(DOCS_PATH, file_name)
            with fitz.open(path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                texts.append(text)
    return texts

def create_document_embeddings():
    texts = load_pdfs()
    
    # Split long texts into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100
    )
    chunks = []
    for text in texts:
        chunks.extend(text_splitter.split_text(text))
    
    # Create embeddings
    embeddings = OpenAIEmbeddings()
    client = chromadb.Client()
    collection = client.create_collection("piwc_documents")
    
    for i, chunk in enumerate(chunks):
        collection.add(
            documents=[chunk],
            metadatas=[{"source": f"pdf_{i}"}],
            ids=[str(i)]
        )
    return collection

# Run once to initialize collection
if __name__ == "__main__":
    create_document_embeddings()
