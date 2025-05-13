import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from llama_index.llms.ollama import Ollama
import google.generativeai as genai

# Load environment variables first
load_dotenv()

# LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL")
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()  # Default to gemini if not specified
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # Correct model name

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")

# Validate required environment variables
if not QDRANT_HOST or not QDRANT_PORT:
    raise ValueError("Missing QDRANT_HOST or QDRANT_PORT in environment variables.")

if LLM_PROVIDER == "ollama" and (not OLLAMA_URL or not LLM_MODEL):
    raise ValueError("When using Ollama, both OLLAMA_URL and LLM_MODEL must be provided.")

if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("When using Gemini, GEMINI_API_KEY must be provided.")

# Configure console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# General logger for the application, other modules can create their own or use this.
logger = logging.getLogger("app") # Root logger for the app module

# Configure file logging for token counts
# Path is relative to WORKDIR in Docker, which is /app.
# So this will create /app/app/logs/token_log.log
# The Dockerfile creates /app/app/logs to ensure it exists.
LOGS_DIR = "app/logs" # Path within the container relative to /app
os.makedirs(LOGS_DIR, exist_ok=True)
token_logger = logging.getLogger("token_logger")
token_handler = logging.FileHandler(os.path.join(LOGS_DIR, "token_log.log"))
token_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
token_logger.addHandler(token_handler)
token_logger.setLevel(logging.INFO)

# Base LLM wrapper class for consistency across providers
class LLMWrapper(ABC):
    """Base abstract class for language model wrappers"""
    
    def __init__(
        self, 
        model: str, 
        temperature: float = 0.1, 
        max_tokens: int = 8192
    ):
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Generate a completion for the given prompt"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the language model"""
        pass
    
    def get_provider_name(self) -> str:
        """Return the name of the provider"""
        return self.__class__.__name__.replace("Wrapper", "")

# Gemini wrapper class
class GeminiWrapper(LLMWrapper):
    """Wrapper for Google's Gemini API"""
    
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        temperature: float = 0.1, 
        max_tokens: int = 8192
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Verify the model exists and list available models if it doesn't
        self._verify_model_and_setup()
    
    def _verify_model_and_setup(self):
        try:
            # Get list of available models
            available_models = genai.list_models()
            model_names = [model.name.split('/')[-1] for model in available_models]
            logger.info(f"Available Gemini models: {', '.join(model_names)}")
            
            # Check if our model is in the list
            if self.model_name not in model_names:
                # If the model isn't available, try to use a fallback
                logger.warning(f"Model '{self.model_name}' not found. Available models: {', '.join(model_names)}")
                
                # Try to find a suitable alternative
                for fallback in ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]:
                    if fallback in model_names:
                        logger.info(f"Using fallback model: {fallback}")
                        self.model_name = fallback
                        break
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                }
            )
            logger.info(f"Successfully initialized Gemini model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Error setting up Gemini: {e}")
            raise
    
    def complete(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            # Return a fallback response
            return f"Error generating response: {str(e)}"
    
    def test_connection(self) -> bool:
        try:
            response = self.complete("Test connection")
            logger.info(f"Gemini test response: {response[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}")
            return False

# Ollama wrapper class
class OllamaWrapper(LLMWrapper):
    """Wrapper for Ollama API"""
    
    def __init__(
        self, 
        model: str, 
        base_url: str, 
        temperature: float = 0.1, 
        max_tokens: int = 8192
    ):
        super().__init__(model, temperature, max_tokens)
        self.base_url = base_url
        
        # Initialize the Ollama client
        self._setup_client()
    
    def _setup_client(self):
        try:
            self.client = Ollama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=self.temperature,
                request_timeout=3600.0
            )
            logger.info(f"Initialized Ollama client for model '{self.model_name}' at {self.base_url}")
        except Exception as e:
            logger.error(f"Error setting up Ollama client: {e}")
            raise
    
    def complete(self, prompt: str) -> str:
        try:
            response = self.client.complete(prompt)
            return str(response)
        except Exception as e:
            logger.error(f"Error generating content with Ollama: {e}")
            return f"Error generating response: {str(e)}"
    
    def test_connection(self) -> bool:
        try:
            response = self.complete("Test connection")
            logger.info(f"Ollama test response: {response[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False

# Factory function to create the appropriate LLM wrapper
def create_llm_wrapper() -> LLMWrapper:
    """Create and return the appropriate LLM wrapper based on environment configuration"""
    
    if LLM_PROVIDER == "ollama":
        logger.info(f"Creating Ollama wrapper for model '{LLM_MODEL}' at {OLLAMA_URL}")
        return OllamaWrapper(
            model=LLM_MODEL,
            base_url=OLLAMA_URL,
            temperature=0.10,
            max_tokens=8192
        )
    else:  # Default to Gemini
        logger.info(f"Creating Gemini wrapper for model '{GEMINI_MODEL}'")
        return GeminiWrapper(
            model=GEMINI_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=0.10,
            max_tokens=8192
        )

# Create the LLM wrapper instance
try:
    llm = create_llm_wrapper()
    
    # Test the connection
    if not llm.test_connection():
        raise ConnectionError(f"Failed to establish connection with {llm.get_provider_name()} LLM")
    
    logger.info(f"Successfully connected to {llm.get_provider_name()} model '{llm.model_name}'")
except Exception as e:
    logger.error(f"Failed to initialize LLM service ({LLM_PROVIDER}): {e}", exc_info=True)
    raise

# Connect to Qdrant
try:
    qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
    logger.info(f"Attempting to connect to Qdrant at {qdrant_url}")
    qdrant = QdrantClient(url=qdrant_url)
    qdrant.get_collections() # Test connection
    logger.info("Successfully connected to Qdrant.")
except Exception as e:
    logger.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
    raise