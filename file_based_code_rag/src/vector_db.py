from typing import List, Optional
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_core.embeddings import Embeddings
from src.llm_embeddings_model import embeddings

class QdrantClient:
    """
    Wrapper around LangChain's QdrantVectorStore.
    Provides methods for adding documents, connecting to existing
    collections, and performing semantic similarity search.
    """

    def __init__(self, qdrant_url: str, collection_name: str, embeddings: Embeddings = embeddings, prefer_grpc: bool = False):
        """
        Args:
            qdrant_url: URL of the Qdrant instance
            embeddings: LangChain Embeddings object
            collection_name: Name of the target Qdrant collection
            prefer_grpc: Use gRPC transport if supported
        """
        self.url = qdrant_url
        self.embeddings = embeddings
        self.collection_name = collection_name
        self.prefer_grpc = prefer_grpc
        self.vector_store: Optional[QdrantVectorStore] = None

    def add_documents(self, docs: List[Document]) -> None:
        """
        Create or replace a Qdrant collection and add documents.

        Args:
            docs: Documents to embed and index
        """
        if not docs:
            raise ValueError("No documents provided for indexing.")

        self.vector_store = QdrantVectorStore.from_documents(
            docs,
            self.embeddings,
            url=self.url,
            prefer_grpc=self.prefer_grpc,
            collection_name=self.collection_name,
        )

    def connect_existing_collection(self) -> None:
        """
        Connect to an already existing Qdrant collection.
        """
        self.vector_store = QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            collection_name=self.collection_name,
            url=self.url,
            prefer_grpc=self.prefer_grpc,
        )

    def query_store(self, query: str, k: int = 4) -> List[Document]:
        """
        Perform similarity search on the active collection.

        Args:
            query: Natural language query
            k: Number of results to retrieve

        Returns:
            List of matching documents
        """
        if self.vector_store is None:
            raise RuntimeError(
                "Vector store not initialized. "
                "Call add_documents() or connect_existing_collection() first."
            )
        return self.vector_store.similarity_search(query, k=k)
