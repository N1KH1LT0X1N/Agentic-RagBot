"""
MediGuard AI RAG-Helper
LLM configuration and initialization

Supports multiple providers:
- Groq (FREE, fast, llama-3.3-70b) - RECOMMENDED
- Google Gemini (FREE tier)
- Ollama (local, for offline use)

Environment Variables (supports both naming conventions):
- Simple: GROQ_API_KEY, GOOGLE_API_KEY, LLM_PROVIDER, GROQ_MODEL, etc.
- Nested: LLM__GROQ_API_KEY, LLM__GOOGLE_API_KEY, LLM__PROVIDER, etc.
"""

import os
import threading
from typing import Literal, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "MediGuard_AI_RAG_Helper")


def _get_env_with_fallback(primary: str, fallback: str, default: str = "") -> str:
    """Get env var with fallback to alternate naming convention."""
    return os.getenv(primary) or os.getenv(fallback) or default


def get_default_llm_provider() -> str:
    """Get default LLM provider dynamically from environment.
    
    Supports both naming conventions:
    - LLM_PROVIDER (simple)
    - LLM__PROVIDER (pydantic nested)
    """
    return _get_env_with_fallback("LLM_PROVIDER", "LLM__PROVIDER", "groq")


def get_groq_api_key() -> str:
    """Get Groq API key from environment (supports both naming conventions)."""
    return _get_env_with_fallback("GROQ_API_KEY", "LLM__GROQ_API_KEY", "")


def get_google_api_key() -> str:
    """Get Google API key from environment (supports both naming conventions)."""
    return _get_env_with_fallback("GOOGLE_API_KEY", "LLM__GOOGLE_API_KEY", "")


def get_groq_model() -> str:
    """Get Groq model from environment (supports both naming conventions)."""
    return _get_env_with_fallback("GROQ_MODEL", "LLM__GROQ_MODEL", "llama-3.3-70b-versatile")


def get_gemini_model() -> str:
    """Get Gemini model from environment (supports both naming conventions)."""
    return _get_env_with_fallback("GEMINI_MODEL", "LLM__GEMINI_MODEL", "gemini-2.0-flash")


# For backward compatibility (but prefer using get_default_llm_provider())
DEFAULT_LLM_PROVIDER = get_default_llm_provider()


def get_chat_model(
    provider: Optional[Literal["groq", "gemini", "ollama"]] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    json_mode: bool = False
):
    """
    Get a chat model from the specified provider.
    
    Args:
        provider: "groq" (free, fast), "gemini" (free), or "ollama" (local)
        model: Model name (provider-specific)
        temperature: Sampling temperature
        json_mode: Whether to enable JSON output mode
    
    Returns:
        LangChain chat model instance
    """
    # Use dynamic lookup to get current provider from environment
    provider = provider or get_default_llm_provider()
    
    if provider == "groq":
        from langchain_groq import ChatGroq
        
        api_key = get_groq_api_key()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment.\n"
                "Get your FREE API key at: https://console.groq.com/keys"
            )
        
        # Use model from environment or default
        model = model or get_groq_model()
        
        return ChatGroq(
            model=model,
            temperature=temperature,
            api_key=api_key,
            model_kwargs={"response_format": {"type": "json_object"}} if json_mode else {}
        )
    
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = get_google_api_key()
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment.\n"
                "Get your FREE API key at: https://aistudio.google.com/app/apikey"
            )
        
        # Use model from environment or default
        model = model or get_gemini_model()
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
    
    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            from langchain_community.chat_models import ChatOllama
        
        model = model or "llama3.1:8b"
        
        return ChatOllama(
            model=model,
            temperature=temperature,
            format='json' if json_mode else None
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'groq', 'gemini', or 'ollama'")


def get_embedding_provider() -> str:
    """Get embedding provider from environment (supports both naming conventions)."""
    return _get_env_with_fallback("EMBEDDING_PROVIDER", "EMBEDDING__PROVIDER", "huggingface")


def get_embedding_model(provider: Optional[Literal["jina", "google", "huggingface", "ollama"]] = None):
    """
    Get embedding model for vector search.
    
    Args:
        provider: "jina" (high-quality), "google" (free), "huggingface" (local), or "ollama" (local)
    
    Returns:
        LangChain embedding model instance
        
    Note:
        For production use, prefer src.services.embeddings.service.make_embedding_service()
        which has automatic fallback chain: Jina → Google → HuggingFace.
    """
    provider = provider or get_embedding_provider()
    
    if provider == "jina":
        # Try Jina AI embeddings first (high quality, 1024d)
        jina_key = _get_env_with_fallback("JINA_API_KEY", "EMBEDDING__JINA_API_KEY", "")
        if jina_key:
            try:
                # Use the embedding service for Jina
                from src.services.embeddings.service import make_embedding_service
                return make_embedding_service()
            except Exception as e:
                print(f"WARN: Jina embeddings failed: {e}")
                print("INFO: Falling back to Google embeddings...")
                return get_embedding_model("google")
        else:
            print("WARN: JINA_API_KEY not found. Falling back to Google embeddings.")
            return get_embedding_model("google")
    
    elif provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        
        api_key = get_google_api_key()
        if not api_key:
            print("WARN: GOOGLE_API_KEY not found. Falling back to HuggingFace embeddings.")
            return get_embedding_model("huggingface")
        
        try:
            return GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key
            )
        except Exception as e:
            print(f"WARN: Google embeddings failed: {e}")
            print("INFO: Falling back to HuggingFace embeddings...")
            return get_embedding_model("huggingface")
    
    elif provider == "huggingface":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    
    elif provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError:
            from langchain_community.embeddings import OllamaEmbeddings
        
        return OllamaEmbeddings(model="nomic-embed-text")
    
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


class LLMConfig:
    """Central configuration for all LLM models"""
    
    def __init__(self, provider: Optional[str] = None, lazy: bool = True):
        """
        Initialize all model clients.
        
        Args:
            provider: LLM provider - "groq" (free), "gemini" (free), or "ollama" (local)
            lazy: If True, defer model initialization until first use (avoids API key errors at import)
        """
        # Store explicit provider or None to use dynamic lookup later
        self._explicit_provider = provider
        self._lazy = lazy
        self._initialized = False
        self._initialized_provider = None  # Track which provider was initialized
        self._lock = threading.Lock()
        
        # Lazy-initialized model instances
        self._planner = None
        self._analyzer = None
        self._explainer = None
        self._synthesizer_7b = None
        self._synthesizer_8b = None
        self._director = None
        self._embedding_model = None
        
        if not lazy:
            self._initialize_models()
    
    @property
    def provider(self) -> str:
        """Get current provider (dynamic lookup if not explicitly set)."""
        return self._explicit_provider or get_default_llm_provider()
    
    def _check_provider_change(self):
        """Check if provider changed and reinitialize if needed."""
        current = self.provider
        if self._initialized and self._initialized_provider != current:
            print(f"Provider changed from {self._initialized_provider} to {current}, reinitializing...")
            self._initialized = False
            self._planner = None
            self._analyzer = None
            self._explainer = None
            self._synthesizer_7b = None
            self._synthesizer_8b = None
            self._director = None
    
    def _initialize_models(self):
        """Initialize all model clients (called on first use if lazy)"""
        self._check_provider_change()
        
        if self._initialized:
            return
        
        with self._lock:
            # Double-checked locking
            if self._initialized:
                return
            
            print(f"Initializing LLM models with provider: {self.provider.upper()}")
        
        # Fast model for structured tasks (planning, analysis)
        self._planner = get_chat_model(
            provider=self.provider,
            temperature=0.0,
            json_mode=True
        )
        
        # Fast model for biomarker analysis and quick tasks
        self._analyzer = get_chat_model(
            provider=self.provider,
            temperature=0.0
        )
        
        # Medium model for RAG retrieval and explanation
        self._explainer = get_chat_model(
            provider=self.provider,
            temperature=0.2
        )
        
        # Configurable synthesizers
        self._synthesizer_7b = get_chat_model(
            provider=self.provider,
            temperature=0.2
        )
        
        self._synthesizer_8b = get_chat_model(
            provider=self.provider,
            temperature=0.2
        )
        
        # Director for Outer Loop
        self._director = get_chat_model(
            provider=self.provider,
            temperature=0.0,
            json_mode=True
        )
        
        # Embedding model for RAG  
        self._embedding_model = get_embedding_model()
        
        self._initialized = True
        self._initialized_provider = self.provider
    
    @property
    def planner(self):
        self._initialize_models()
        return self._planner
    
    @property
    def analyzer(self):
        self._initialize_models()
        return self._analyzer
    
    @property
    def explainer(self):
        self._initialize_models()
        return self._explainer
    
    @property
    def synthesizer_7b(self):
        self._initialize_models()
        return self._synthesizer_7b
    
    @property
    def synthesizer_8b(self):
        self._initialize_models()
        return self._synthesizer_8b
    
    @property
    def director(self):
        self._initialize_models()
        return self._director
    
    @property
    def embedding_model(self):
        self._initialize_models()
        return self._embedding_model
    
    def get_synthesizer(self, model_name: Optional[str] = None):
        """Get synthesizer model (for backward compatibility)"""
        if model_name:
            return get_chat_model(provider=self.provider, model=model_name, temperature=0.2)
        return self.synthesizer_8b
    
    def print_config(self):
        """Print current LLM configuration"""
        print("=" * 60)
        print("MediGuard AI RAG-Helper - LLM Configuration")
        print("=" * 60)
        print(f"Provider:      {self.provider.upper()}")
        
        if self.provider == "groq":
            print(f"Model:         llama-3.3-70b-versatile (FREE)")
        elif self.provider == "gemini":
            print(f"Model:         gemini-2.0-flash (FREE)")
        else:
            print(f"Model:         llama3.1:8b (local)")
        
        print(f"Embeddings:    Google Gemini (FREE)")
        print("=" * 60)


# Global LLM configuration instance
llm_config = LLMConfig()


def check_api_connection():
    """Verify API connection and keys are configured"""
    provider = DEFAULT_LLM_PROVIDER
    
    try:
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                print("WARN: GROQ_API_KEY not set")
                print("\n  Get your FREE API key at:")
                print("  https://console.groq.com/keys")
                return False
            
            # Test connection
            test_model = get_chat_model("groq")
            response = test_model.invoke("Say 'OK' in one word")
            print("OK: Groq API connection successful")
            return True
            
        elif provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print("WARN: GOOGLE_API_KEY not set")
                print("\n  Get your FREE API key at:")
                print("  https://aistudio.google.com/app/apikey")
                return False
            
            test_model = get_chat_model("gemini")
            response = test_model.invoke("Say 'OK' in one word")
            print("OK: Google Gemini API connection successful")
            return True
            
        else:
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                from langchain_community.chat_models import ChatOllama
            test_model = ChatOllama(model="llama3.1:8b")
            response = test_model.invoke("Hello")
            print("OK: Ollama connection successful")
            return True
            
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    llm_config.print_config()
    check_api_connection()
