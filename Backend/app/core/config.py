# Backend/app/core/config.py
import os
import logging
from typing import Dict, Any, Optional, Callable
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

# Function-based LLM implementation

def setup_gemini(model_name: str, api_key: str, temperature: float = 0.1, max_tokens: int = 8192):
    """
    Set up and configure a Gemini LLM client
    
    Args:
        model_name: The name of the Gemini model to use
        api_key: The Gemini API key
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Dict containing the model and helper functions
    """
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # Get list of available models and find valid one
    available_models = genai.list_models()
    model_names = [model.name.split('/')[-1] for model in available_models]
    logger.info(f"Available Gemini models: {', '.join(model_names)}")
    
    # Check if requested model exists, use fallback if not
    if model_name not in model_names:
        logger.warning(f"Model '{model_name}' not found. Available models: {', '.join(model_names)}")
        
        # Try to find a suitable alternative
        for fallback in ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]:
            if fallback in model_names:
                logger.info(f"Using fallback model: {fallback}")
                model_name = fallback
                break
    
    # Initialize the model
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
    )
    logger.info(f"Successfully initialized Gemini model: {model_name}")
    
    # Define completion function
    def complete(prompt: str) -> str:
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            return f"Error generating response: {str(e)}"
            
    # Define test function
    def test_connection() -> bool:
        try:
            response = complete("Test connection")
            logger.info(f"Gemini test response: {response[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gemini: {e}")
            return False
    
    # Return model config
    return {
        "model_name": model_name,
        "model": model,
        "provider": "gemini",
        "complete": complete,
        "test_connection": test_connection
    }

def setup_ollama(model_name: str, base_url: str, temperature: float = 0.1, max_tokens: int = 8192):
    """
    Set up and configure an Ollama LLM client
    
    Args:
        model_name: The name of the Ollama model to use
        base_url: The Ollama API base URL
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate
        
    Returns:
        Dict containing the model and helper functions
    """
    # Initialize Ollama client
    try:
        client = Ollama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            request_timeout=3600.0
        )
        logger.info(f"Initialized Ollama client for model '{model_name}' at {base_url}")
        
        # Define completion function
        def complete(prompt: str) -> str:
            try:
                response = client.complete(prompt)
                return str(response)
            except Exception as e:
                logger.error(f"Error generating content with Ollama: {e}")
                return f"Error generating response: {str(e)}"
        
        # Define test function
        def test_connection() -> bool:
            try:
                response = complete("Test connection")
                logger.info(f"Ollama test response: {response[:50]}...")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                return False
        
        # Return model config
        return {
            "model_name": model_name,
            "model": client,
            "provider": "ollama",
            "complete": complete,
            "test_connection": test_connection
        }
        
    except Exception as e:
        logger.error(f"Error setting up Ollama client: {e}")
        raise

# Initialize LLM based on provider
try:
    if LLM_PROVIDER == "ollama":
        logger.info(f"Setting up Ollama model '{LLM_MODEL}' at {OLLAMA_URL}")
        llm = setup_ollama(
            model_name=LLM_MODEL,
            base_url=OLLAMA_URL,
            temperature=0.10,
            max_tokens=8192
        )
    else:  # Default to Gemini
        logger.info(f"Setting up Gemini model '{GEMINI_MODEL}'")
        llm = setup_gemini(
            model_name=GEMINI_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=0.10,
            max_tokens=8192
        )
    
    # Test the connection
    if not llm["test_connection"]():
        raise ConnectionError(f"Failed to establish connection with {llm['provider']} LLM")
    
    logger.info(f"Successfully connected to {llm['provider']} model '{llm['model_name']}'")
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