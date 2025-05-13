import json
import re
import logging
import os

logger = logging.getLogger(__name__)

def load_prompt_template():
    prompt_file_path = os.getenv("PROMPT_FILE_PATH", "app/data/prompt.txt") # Default if env var not set
    try:
        # Ensure the path is relative to the application root if using default
        # If PROMPT_FILE_PATH is absolute, os.path.join will handle it.
        # In Docker, with WORKDIR /app, and files in /app/app/data, this should be:
        # PROMPT_FILE_PATH=/app/app/data/prompt.txt (set in Dockerfile)
        # The default "app/data/prompt.txt" would resolve to "/app/app/data/prompt.txt"
        # if the script is run from /app.
        
        # If PROMPT_FILE_PATH is /app/app/data/prompt.txt as set in Dockerfile, it's absolute
        # and will be used directly.
        
        with open(prompt_file_path, "r") as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at: {prompt_file_path}. Using default prompt.")
        return """Analyze the following logs:\n{logs}\nProvide a summary and identify anomalies. Return valid JSON.\nSchema: {model_schema}"""
    except Exception as e:
        logger.error(f"Error loading prompt file {prompt_file_path}: {e}. Using default prompt.")
        return """Analyze the following logs:\n{logs}\nProvide a summary and identify anomalies. Return valid JSON.\nSchema: {model_schema}"""


def clean_and_parse_json(raw_text: str):
    if not raw_text or not isinstance(raw_text, str):
        return None, "Invalid or empty response text"
    
    # First attempt: direct parsing
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError:
        logger.info("Direct JSON parsing failed, attempting to clean response...")
    
    # Second attempt: extract from markdown code block
    if "```json" in raw_text or "```" in raw_text:
        try:
            if "```json" in raw_text:
                json_block = raw_text.split("```json")[1].split("```")[0].strip()
            else:
                # Try with just triple backticks
                json_block = raw_text.split("```")[1].strip() # Potential IndexError if only one ```
            return json.loads(json_block), None
        except (IndexError, json.JSONDecodeError) as e:
            logger.warning(f"Code block extraction failed: {e}")
            # Fall through if ``` was present but not a valid block
    
    # Third attempt: find outermost braces
    try:
        json_start = raw_text.find('{')
        json_end = raw_text.rfind('}')
        if json_start >= 0 and json_end > json_start:
            potential_json = raw_text[json_start:json_end+1]
            return json.loads(potential_json), None
    except json.JSONDecodeError as e:
        logger.warning(f"Brace extraction failed: {e}")
    
    # Fourth attempt: more aggressive cleaning
    try:
        # Remove common problematic characters
        cleaned_text = raw_text.replace('\n', ' ').replace('\r', ' ')
        # Find the first { and last }
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}')
        if json_start >= 0 and json_end > json_start:
            potential_json = cleaned_text[json_start:json_end+1]
            # Try to fix common JSON issues
            potential_json = potential_json.replace("'", '"')  # Replace single quotes
            potential_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', potential_json)  # Quote unquoted keys
            return json.loads(potential_json), None
    except Exception as e:
        logger.warning(f"Aggressive cleaning failed: {e}")
    
    error_msg = "Could not parse response as valid JSON after multiple attempts."
    logger.error(error_msg)
    logger.error(f"Raw response: {raw_text[:500]}...")  # Log first 500 chars for debugging
    return None, error_msg


def count_tokens(text: str) -> int:
    if not text: return 0
    words = len(text.split())
    chars = len(text)
    # This is a very rough approximation.
    # A common heuristic is ~4 chars per token, or use len(text)/2.5 for OpenAI models.
    # For word-based models, word count might be closer.
    # Ollama tokenization depends on the specific model.
    estimated_tokens = words + (chars // 10) # Original formula
    return estimated_tokens if estimated_tokens > 0 else 1