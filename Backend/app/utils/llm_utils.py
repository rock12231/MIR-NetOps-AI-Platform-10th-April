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
    
    # Fifth attempt: handle markdown-formatted responses (e.g., with headers and sections)
    try:
        # Remove markdown headers and other formatting
        cleaned_md = re.sub(r'#{1,6}\s+.*?\n', '', raw_text)  # Remove headers
        cleaned_md = re.sub(r'\*\*|\*|__|\s+_', '', cleaned_md)  # Remove bold/italic markers
        cleaned_md = re.sub(r'\n\s*[-*]\s+', '\n', cleaned_md)  # Remove list markers
        
        # Remove common text phrases that might appear before JSON
        prefixes_to_remove = [
            "Here's the analysis:", "Here is the analysis:", 
            "Analysis:", "Response:", "Summary:", "JSON response:",
            "The analysis of the logs:", "Here's a summary:",
            "Here's the JSON:"
        ]
        for prefix in prefixes_to_remove:
            if prefix in cleaned_md:
                parts = cleaned_md.split(prefix, 1)
                cleaned_md = parts[1].strip()
        
        # Try to find the JSON object again
        json_start = cleaned_md.find('{')
        json_end = cleaned_md.rfind('}')
        if json_start >= 0 and json_end > json_start:
            potential_json = cleaned_md[json_start:json_end+1]
            # Try to fix common JSON issues
            potential_json = potential_json.replace("'", '"')
            potential_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', potential_json)
            return json.loads(potential_json), None
    except Exception as e:
        logger.warning(f"Markdown cleaning attempt failed: {e}")
    
    # Final fallback: try to construct a minimally valid JSON
    try:
        logger.warning("All parsing attempts failed, attempting to construct fallback JSON")
        
        # Extract what appears to be a summary
        summary_match = re.search(r'summary|overview|analysis', raw_text, re.IGNORECASE)
        summary = "Failed to parse response as valid JSON. See logs for details."
        if summary_match:
            # Find potential summary text
            start_idx = summary_match.start()
            end_idx = raw_text.find('\n\n', start_idx)
            if end_idx == -1:
                end_idx = len(raw_text)
            potential_summary = raw_text[start_idx:end_idx].strip()
            # Clean up the summary
            summary = re.sub(r'^\W*summary\W*', '', potential_summary, flags=re.IGNORECASE)
            summary = summary.strip('":* \t\n').strip()
            if len(summary) > 10:  # Only use if it's substantial
                summary = f"Parsing failed, extracted summary: {summary[:200]}"
        
        # Create a fallback JSON
        fallback_json = {
            "summary": summary,
            "normal_patterns": ["Unable to parse normal patterns"],
            "anomalies": [{
                "description": "Failed to parse LLM response as valid JSON",
                "severity": "Medium",
                "requires_review": True,
                "reasoning": "The system could not interpret the LLM's analysis"
            }],
            "recommendations": ["Review raw logs manually", "Check if LLM prompt needs adjustment"],
            "devices_analyzed": [],
            "locations_analyzed": [],
            "parsing_error": True
        }
        logger.warning("Returning fallback JSON due to parsing failure")
        return fallback_json, "Used fallback JSON structure due to parsing failure"
    except Exception as e:
        logger.error(f"Fallback JSON construction failed: {e}")
    
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