from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import os
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "devops_knowledge",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None
        self._embedding_function = None

    async def initialize(self):
        os.makedirs(self.persist_directory, exist_ok=True)

        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self._client = chromadb.Client(
                Settings(
                    persist_directory=self.persist_directory,
                    anonymized_telemetry=False,
                )
            )

            self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self._embedding_function,
                metadata={"description": "DevOps Agent Knowledge Base"},
            )

            logger.info(f"Vector store initialized with {self._collection.count()} documents")

        except ImportError:
            logger.warning("ChromaDB or sentence-transformers not installed, using mock mode")
            self._client = None

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> bool:
        if not self._collection:
            logger.warning("Vector store not initialized, using mock mode")
            return True

        try:
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]

            self._collection.add(
                documents=documents,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids,
            )

            logger.info(f"Added {len(documents)} documents to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False

    async def search(
        self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        if not self._collection:
            return self._mock_search(query, top_k)

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            return [
                {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"][0] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                }
                for i in range(len(results["ids"][0]))
            ]

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return self._mock_search(query, top_k)

    def _mock_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        return [
            {
                "id": f"mock_doc_{i}",
                "content": f"Mock content for query: {query[:50]}...",
                "metadata": {"source": "mock", "type": "knowledge"},
                "distance": 0.1 * i,
                "score": 1.0 - 0.1 * i,
            }
            for i in range(min(top_k, 3))
        ]

    async def delete(self, ids: List[str]) -> bool:
        if not self._collection:
            return True

        try:
            self._collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self._collection:
            return {"count": 0, "status": "mock"}

        return {
            "count": self._collection.count(),
            "name": self.collection_name,
            "status": "ready",
        }
