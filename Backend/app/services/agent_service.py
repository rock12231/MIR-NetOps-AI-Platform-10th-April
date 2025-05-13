from typing import List, Dict, Optional
import logging

from app.core.config import LLM_MODEL as CFG_LLM_MODEL, llm # Import LLM client and model name
from app.core.models import RouterAgentResponse, ChatCompletionResponse # Pydantic models

logger = logging.getLogger(__name__)

# This class holds settings for the RouterAgent, mirroring original structure
class RouterAgentSettings:
    LLM_MODEL: str = CFG_LLM_MODEL # Use the imported model name from config
    LLM_TEMPERATURE: float = 0.10
    MAX_TOKENS: int = 4096 # Default, can be made configurable

class RouterAgentTool:
    def __init__(self, name: str, description: str):
        # Create a mock metadata object similar to LlamaIndex tool metadata
        self.metadata = type('ToolMetadata', (), {'name': name, 'description': description})()

class RouterAgentSessionManager:
    def __init__(self):
        self.sessions: Dict[str, List[Dict[str, str]]] = {} # Store conversation history per session

    def get_active_sessions_count(self) -> int:
        return len(self.sessions)

    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id} reset.")

    def add_to_session(self, session_id: str, message: Dict[str, str]):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(message)

    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])


class RouterAgent:
    def __init__(self):
        self.settings = RouterAgentSettings()
        self.tools = [
            RouterAgentTool("log_analyzer", "Analyzes network logs based on user queries."),
            RouterAgentTool("query_processor", "Processes general user queries using the LLM.")
        ]
        self.session_manager = RouterAgentSessionManager()
        logger.info(f"RouterAgent initialized with LLM: {self.settings.LLM_MODEL}")

    async def query(self, query_text: str, session_id: str) -> RouterAgentResponse:
        # For a simple query, we might directly ask the LLM
        # You could build a more complex prompt here using session history or context
        
        # Add current query to session
        self.session_manager.add_to_session(session_id, {"role": "user", "content": query_text})
        
        # Create a prompt - example: just use the latest query
        # For a more conversational agent, you'd include history from self.session_manager.get_session_history(session_id)
        prompt = f"User query: {query_text}\n\nProvide a concise and helpful answer."

        try:
            logger.info(f"Agent processing query for session {session_id}: '{query_text[:50]}...'")
            response_text = llm.complete(prompt) # Use the global llm client
            
            # Add LLM response to session
            self.session_manager.add_to_session(session_id, {"role": "assistant", "content": str(response_text)})

            return RouterAgentResponse(
                status="success",
                response=str(response_text),
                metadata={"session_id": session_id, "llm_model": self.settings.LLM_MODEL}
            )
        except Exception as e:
            logger.error(f"RouterAgent query failed for session {session_id}: {e}", exc_info=True)
            return RouterAgentResponse(
                status="error",
                response="Query processing failed.",
                error=str(e),
                metadata={"session_id": session_id}
            )

    async def chat_openai(self, messages: List[Dict[str, str]], session_id: str) -> ChatCompletionResponse:
        # This method aims to be OpenAI compatible.
        # messages typically: [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}, ...]
        
        # Add latest user message to session
        if messages and messages[-1]["role"] == "user":
            self.session_manager.add_to_session(session_id, messages[-1])
        
        # Construct prompt from messages list (or use session history + new messages)
        # A simple approach: concatenate content of all messages.
        # A better one: use the model's specific chat prompt templating if available, or format carefully.
        
        # Get full session history including the new messages
        # current_conversation = self.session_manager.get_session_history(session_id) + messages # If messages are new additions
        # For this mock, let's assume `messages` is the complete history for this turn.
        
        # This is a simplified way to create a single prompt string.
        # Real chat models handle structured message lists better.
        # Ollama's `chat` method (if using `llm.chat`) would take `messages` directly.
        # Since `llm.complete` takes a string, we format it.
        prompt_parts = []
        for msg in messages:
            prompt_parts.append(f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}")
        prompt = "\n".join(prompt_parts)

        try:
            logger.info(f"Agent processing chat completion for session {session_id}, last message: '{messages[-1]['content'][:50]}...'")
            response_text = llm.complete(prompt)

            # Add LLM response to session
            self.session_manager.add_to_session(session_id, {"role": "assistant", "content": str(response_text)})
            
            return ChatCompletionResponse(
                status="success",
                response=str(response_text), # Ollama `complete` returns CompletionResponse, extract text
                metadata={"session_id": session_id, "llm_model": self.settings.LLM_MODEL}
            )
        except Exception as e:
            logger.error(f"RouterAgent chat_openai failed for session {session_id}: {e}", exc_info=True)
            return ChatCompletionResponse(
                status="error",
                response="Chat completion failed.",
                error=str(e),
                metadata={"session_id": session_id}
            )

    async def reset_conversation(self, session_id: str):
        self.session_manager.reset_session(session_id)
        logger.info(f"Conversation reset for session_id: {session_id}")

    async def health_check(self) -> Dict:
        # Perform a quick check on the LLM
        llm_ok = False
        try:
            llm.complete("health check ping") # Send a very short test prompt
            llm_ok = True
        except Exception:
            llm_ok = False
            
        return {
            "status": "healthy" if llm_ok else "degraded",
            "llm_available": llm_ok,
            "tools_available_count": len(self.tools)
        }