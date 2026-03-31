"""
RAG Document Ingestion Pipeline.
Loads financial context PDFs, chunks them, and stores them in a Vector DB.
"""

class RAGIngestionPipeline:
    def __init__(self, vector_db_path: str):
        self.vector_db_path = vector_db_path

    def ingest_document(self, filepath: str) -> int:
        """Reads a PDF, chunks it, and embeds it into the vector database."""
        # TODO in Implementation:
        # 1. loader = PyPDFLoader(filepath)
        # 2. docs = loader.load()
        # 3. text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # 4. splits = text_splitter.split_documents(docs)
        # 5. embeddings = OpenAIEmbeddings()
        # 6. vector_store.add_documents(splits)
        # return len(splits)
        raise NotImplementedError("Stub: paper trading MVPs only")
