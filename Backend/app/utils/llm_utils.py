# Backend/app/utils/llm_utils.py
import json
import re
import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def load_prompt_template():
    # Possible prompt file locations
    possible_paths = [
        os.getenv("PROMPT_FILE_PATH"),  # 1. Environment variable (highest priority)
        "app/app/data/prompt.txt",      # 2. Docker path (WORKDIR /app)
        "Backend/data/prompt.txt",      # 3. Local development path
        "data/prompt.txt",              # 4. Relative from current directory
        Path(__file__).parent.parent.parent / "data" / "prompt.txt"  # 5. From module location
    ]
    
    # Filter out None values (if env var is not set)
    possible_paths = [p for p in possible_paths if p]
    
    # Try each path until we find a valid file
    for prompt_file_path in possible_paths:
        try:
            logger.info(f"Attempting to load prompt from: {prompt_file_path}")
            with open(prompt_file_path, "r") as file:
                prompt_content = file.read()
                logger.info(f"Successfully loaded prompt from: {prompt_file_path}")
                return prompt_content
        except FileNotFoundError:
            logger.debug(f"Prompt file not found at: {prompt_file_path}")
            continue
        except Exception as e:
            logger.warning(f"Error loading prompt file {prompt_file_path}: {e}")
            continue
    
    # If we get here, none of the paths worked
    logger.error("Failed to find valid prompt file at any of the expected locations. Using default prompt.")
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


def count_tokens(text: str, provider: Optional[str] = None) -> int:
    """
    Estimate token count for the given text based on provider.
    
    Args:
        text: The text to count tokens for
        provider: The LLM provider (e.g., "ollama", "gemini")
    
    Returns:
        Estimated token count
    """
    if not text: 
        return 0
    
    # Get provider from environment if not passed
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
    words = len(text.split())
    chars = len(text)
    
    # Different estimation methods based on provider
    if provider == "gemini":
        # Gemini tends to use fewer tokens, roughly 100 chars = 25 tokens
        # This is an approximation, 1 token ≈ 4 chars
        estimated_tokens = chars // 4
    elif provider == "ollama":
        # Ollama tokenization depends on the specific model, using original formula
        estimated_tokens = words + (chars // 10)
    else:
        # Default fallback method
        # Using a middle ground between character and word-based models
        estimated_tokens = words + (chars // 6)
    
    return max(1, estimated_tokens)