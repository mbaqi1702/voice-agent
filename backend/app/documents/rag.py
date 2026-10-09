"""
Simple RAG pipeline using LlamaIndex + Chroma.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger

from app.config import get_settings
from app.documents.loader import load_text_from_file


class DocumentRAG:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._index = None
        self._initialized = False

    def _ensure_index(self) -> None:
        if self._initialized:
            return

        try:
            from llama_index.core import (
                Document,
                Settings,
                StorageContext,
                VectorStoreIndex,
                load_index_from_storage,
            )
            from llama_index.core.node_parser import SentenceSplitter
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            from llama_index.vector_stores.chroma import ChromaVectorStore
            import chromadb

            # Use a lightweight local embedding model (free)
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-small-en-v1.5"
            )
            Settings.chunk_size = 512
            Settings.chunk_overlap = 50

            chroma_client = chromadb.PersistentClient(
                path=str(self.settings.vector_store_dir)
            )
            chroma_collection = chroma_client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # Try to load existing index
            try:
                self._index = load_index_from_storage(storage_context)
                logger.info("Loaded existing vector index")
            except Exception:
                self._index = VectorStoreIndex.from_documents(
                    [], storage_context=storage_context
                )
                logger.info("Created new empty vector index")

            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
            self._initialized = False

    def ingest_file(self, path: Path) -> str:
        """Load a file, chunk it, and add to the vector store."""
        self._ensure_index()
        if not self._index:
            return "RAG system is not available."

        try:
            text = load_text_from_file(path)
            from llama_index.core import Document

            doc = Document(
                text=text,
                metadata={"filename": path.name, "source": str(path)},
            )
            self._index.insert(doc)
            logger.info(f"Ingested {path.name} into vector store")
            return f"Successfully indexed document: {path.name}"
        except Exception as e:
            logger.exception(f"Ingest failed for {path}")
            return f"Failed to index {path.name}: {e}"

    def query(self, question: str, top_k: int = 4) -> str:
        """Retrieve relevant chunks and return a grounded answer context."""
        self._ensure_index()
        if not self._index:
            return "RAG system is not available. Please try again later."

        try:
            query_engine = self._index.as_query_engine(similarity_top_k=top_k)
            response = query_engine.query(question)
            return str(response)
        except Exception as e:
            logger.exception("RAG query failed")
            return f"Could not search documents: {e}"

    def get_full_text(self, filename: str) -> Optional[str]:
        """Return the full extracted text of a document for dictation."""
        path = self.settings.documents_dir / filename
        if not path.exists():
            return None
        try:
            return load_text_from_file(path)
        except Exception as e:
            logger.error(f"Could not load {filename}: {e}")
            return None


# Singleton
rag_service = DocumentRAG()
