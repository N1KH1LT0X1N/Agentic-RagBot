"""
MediGuard AI RAG-Helper
PDF document processing and vector store creation
"""

import os
from pathlib import Path
from typing import List, Optional, Literal
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()


def get_embedding_model(provider: Literal["google", "huggingface", "ollama"] = None):
    """
    Get embedding model with automatic fallback.
    
    Args:
        provider: "google" (FREE, recommended), "huggingface" (local), or "ollama" (local)
    
    Returns:
        Embedding model instance
    """
    provider = provider or os.getenv("EMBEDDING_PROVIDER", "google")
    
    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("⚠️  GOOGLE_API_KEY not found in .env file")
            print("   Get FREE API key: https://aistudio.google.com/app/apikey")
            print("   Falling back to HuggingFace local embeddings...\n")
            return get_embedding_model("huggingface")
        
        try:
            print("✓ Using Google Gemini embeddings (FREE, fast)")
            return GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key
            )
        except Exception as e:
            print(f"⚠️  Google embeddings failed: {e}")
            print("   Falling back to HuggingFace local embeddings...\n")
            return get_embedding_model("huggingface")
    
    elif provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        
        print("✓ Using HuggingFace local embeddings (free, offline)")
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    
    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        
        print("✓ Using local Ollama embeddings (requires Ollama running)")
        return OllamaEmbeddings(model="nomic-embed-text")
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'google', 'huggingface', or 'ollama'")


class PDFProcessor:
    """Handles medical PDF ingestion and vector store creation"""
    
    def __init__(
        self,
        pdf_directory: str = "data/medical_pdfs",
        vector_store_path: str = "data/vector_stores",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize PDF processor.
        
        Args:
            pdf_directory: Path to folder containing medical PDFs
            vector_store_path: Path to save FAISS vector stores
            chunk_size: Size of text chunks for RAG
            chunk_overlap: Overlap between chunks (preserves context)
        """
        self.pdf_directory = Path(pdf_directory)
        self.vector_store_path = Path(vector_store_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create directories if they don't exist
        self.pdf_directory.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Text splitter with medical context awareness
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len
        )
    
    def load_pdfs(self) -> List[Document]:
        """
        Load all PDF documents from the configured directory.
        
        Returns:
            List of Document objects with content and metadata
        """
        print(f"Loading PDFs from: {self.pdf_directory}")
        
        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"⚠️  No PDF files found in {self.pdf_directory}")
            print(f"   Please place medical PDFs in this directory")
            return []
        
        print(f"Found {len(pdf_files)} PDF file(s):")
        for pdf in pdf_files:
            print(f"  - {pdf.name}")
        
        documents = []
        
        for pdf_path in pdf_files:
            try:
                loader = PyPDFLoader(str(pdf_path))
                docs = loader.load()
                
                # Add source filename to metadata
                for doc in docs:
                    doc.metadata['source_file'] = pdf_path.name
                    doc.metadata['source_path'] = str(pdf_path)
                
                documents.extend(docs)
                print(f"  ✓ Loaded {len(docs)} pages from {pdf_path.name}")
                
            except Exception as e:
                print(f"  ✗ Error loading {pdf_path.name}: {e}")
        
        print(f"\nTotal: {len(documents)} pages loaded from {len(pdf_files)} PDF(s)")
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks for RAG retrieval.
        
        Args:
            documents: List of loaded documents
        
        Returns:
            List of chunked documents with preserved metadata
        """
        print(f"\nChunking documents (size={self.chunk_size}, overlap={self.chunk_overlap})...")
        
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_id'] = i
        
        print(f"✓ Created {len(chunks)} chunks from {len(documents)} pages")
        print(f"  Average chunk size: {sum(len(c.page_content) for c in chunks) // len(chunks)} characters")
        
        return chunks
    
    def create_vector_store(
        self,
        chunks: List[Document],
        embedding_model,
        store_name: str = "medical_knowledge"
    ) -> FAISS:
        """
        Create FAISS vector store from document chunks.
        
        Args:
            chunks: Document chunks to embed
            embedding_model: Embedding model (from llm_config)
            store_name: Name for the vector store
        
        Returns:
            FAISS vector store object
        """
        print(f"\nCreating vector store: {store_name}")
        print(f"Generating embeddings for {len(chunks)} chunks...")
        print("(This may take a few minutes...)")
        
        # Create FAISS vector store
        vector_store = FAISS.from_documents(
            documents=chunks,
            embedding=embedding_model
        )
        
        # Save to disk
        save_path = self.vector_store_path / f"{store_name}.faiss"
        vector_store.save_local(str(self.vector_store_path), index_name=store_name)
        
        print(f"✓ Vector store created and saved to: {save_path}")
        
        return vector_store
    
    def load_vector_store(
        self,
        embedding_model,
        store_name: str = "medical_knowledge"
    ) -> Optional[FAISS]:
        """
        Load existing vector store from disk.
        
        Args:
            embedding_model: Embedding model (must match the one used to create store)
            store_name: Name of the vector store
        
        Returns:
            FAISS vector store or None if not found
        """
        store_path = self.vector_store_path / f"{store_name}.faiss"
        
        if not store_path.exists():
            print(f"⚠️  Vector store not found: {store_path}")
            return None
        
        try:
            vector_store = FAISS.load_local(
                str(self.vector_store_path),
                embedding_model,
                index_name=store_name,
                allow_dangerous_deserialization=True
            )
            print(f"✓ Loaded vector store from: {store_path}")
            return vector_store
        
        except Exception as e:
            print(f"✗ Error loading vector store: {e}")
            return None
    
    def create_retrievers(
        self,
        embedding_model,
        store_name: str = "medical_knowledge",
        force_rebuild: bool = False
    ) -> dict:
        """
        Create or load retrievers for RAG.
        
        Args:
            embedding_model: Embedding model
            store_name: Vector store name
            force_rebuild: If True, rebuild vector store even if it exists
        
        Returns:
            Dictionary of retrievers for different purposes
        """
        # Try to load existing store
        if not force_rebuild:
            vector_store = self.load_vector_store(embedding_model, store_name)
        else:
            vector_store = None
        
        # If not found, create new one
        if vector_store is None:
            print("\nBuilding new vector store from PDFs...")
            documents = self.load_pdfs()
            
            if not documents:
                print("⚠️  No documents to process. Please add PDF files.")
                return {}
            
            chunks = self.chunk_documents(documents)
            vector_store = self.create_vector_store(chunks, embedding_model, store_name)
        
        # Create specialized retrievers
        retrievers = {
            "disease_explainer": vector_store.as_retriever(
                search_kwargs={"k": 5}
            ),
            "biomarker_linker": vector_store.as_retriever(
                search_kwargs={"k": 3}
            ),
            "clinical_guidelines": vector_store.as_retriever(
                search_kwargs={"k": 3}
            ),
            "general": vector_store.as_retriever(
                search_kwargs={"k": 5}
            )
        }
        
        print(f"\n✓ Created {len(retrievers)} specialized retrievers")
        return retrievers


def setup_knowledge_base(embedding_model=None, force_rebuild: bool = False, use_configured_embeddings: bool = True):
    """
    Convenience function to set up the complete knowledge base.
    
    Args:
        embedding_model: Embedding model (optional if use_configured_embeddings=True)
        force_rebuild: Force rebuild of vector stores
        use_configured_embeddings: Use embedding provider from EMBEDDING_PROVIDER env var
    
    Returns:
        Dictionary of retrievers ready for use
    """
    print("=" * 60)
    print("Setting up Medical Knowledge Base")
    print("=" * 60)
    
    # Use configured embedding provider from environment
    if use_configured_embeddings and embedding_model is None:
        embedding_model = get_embedding_model()
        print("   > Embeddings model loaded")
    elif embedding_model is None:
        raise ValueError("Must provide embedding_model or set use_configured_embeddings=True")
    
    processor = PDFProcessor()
    retrievers = processor.create_retrievers(
        embedding_model,
        store_name="medical_knowledge",
        force_rebuild=force_rebuild
    )
    
    if retrievers:
        print("\n✓ Knowledge base setup complete!")
    else:
        print("\n⚠️  Knowledge base setup incomplete. Add PDFs and try again.")
    
    print("=" * 60)
    
    return retrievers


def get_all_retrievers(force_rebuild: bool = False) -> dict:
    """
    Quick function to get all retrievers using configured embedding provider.
    Used by workflow.py to initialize the Clinical Insight Guild.
    
    Uses EMBEDDING_PROVIDER from .env: "google" (default), "huggingface", or "ollama"
    
    Args:
        force_rebuild: Force rebuild of vector stores
    
    Returns:
        Dictionary of retrievers for all agent types
    """
    return setup_knowledge_base(
        use_configured_embeddings=True,
        force_rebuild=force_rebuild
    )


if __name__ == "__main__":
    # Test PDF processing
    import sys
    from pathlib import Path
    
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("\n" + "="*70)
    print("MediGuard AI - PDF Knowledge Base Builder")
    print("="*70)
    print("\nUsing configured embedding provider from .env")
    print("   EMBEDDING_PROVIDER options: google (default), huggingface, ollama")
    print("="*70)
    
    retrievers = setup_knowledge_base(
        use_configured_embeddings=True,  # Use configured provider
        force_rebuild=False
    )
    
    if retrievers:
        print("\n✓ PDF processing test successful!")
        print(f"Available retrievers: {list(retrievers.keys())}")
