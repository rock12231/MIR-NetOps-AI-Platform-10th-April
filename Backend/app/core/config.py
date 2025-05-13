import os
import logging
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from llama_index.llms.ollama import Ollama

# Load environment variables first
load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL")
LLM_MODEL = os.getenv("LLM_MODEL")
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")

if not OLLAMA_URL or not LLM_MODEL or not QDRANT_HOST or not QDRANT_PORT:
    raise ValueError("Missing OLLAMA_URL, LLM_MODEL, QDRANT_HOST, or QDRANT_PORT in environment variables.")

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

# Configure Ollama
try:
    llm = Ollama(
        model=LLM_MODEL,
        base_url=OLLAMA_URL,
        temperature=0.10,
        request_timeout=3600.0
    )
    # Test connection during initialization
    llm.complete("Test connection")
    logger.info(f"Successfully connected to Ollama model '{LLM_MODEL}' at {OLLAMA_URL}")
except Exception as e:
    logger.error(f"Failed to connect to Ollama: {e}", exc_info=True)
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