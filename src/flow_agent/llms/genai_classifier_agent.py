from threading import Lock

from google import genai
from google.genai import types
from google.genai.chats import AsyncChat
from google.genai.client import AsyncClient

MODEL_DEFAULT = "gemini-2.5-flash-lite"
_lock = Lock()
_genai_chat: AsyncChat | None = None
_llm_client: AsyncClient | None = None

_GENAI_PROMPT = """
You are a helpful agent.
"""

# Define safety settings for ALL categories
_safety_settings = [
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="BLOCK_LOW_AND_ABOVE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_LOW_AND_ABOVE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="BLOCK_LOW_AND_ABOVE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="BLOCK_LOW_AND_ABOVE",
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_CIVIC_INTEGRITY",
        threshold="BLOCK_LOW_AND_ABOVE",
    ),
]


# ---------- Gemini chat singletons ----------
def _create_client():
    global _llm_client
    if _llm_client is None:
        with _lock:
            if _llm_client is None:
                _llm_client = genai.Client().aio
    return _llm_client


async def get_combiner_agent() -> AsyncChat:
    global _genai_chat
    _create_client()
    if _genai_chat is None:
        with _lock:
            if _genai_chat is None:
                _genai_chat = _llm_client.chats.create(
                    model=MODEL_DEFAULT,
                    config=types.GenerateContentConfig(
                        system_instruction=_GENAI_PROMPT,
                        safety_settings=_safety_settings
                    )
                )
    return _genai_chat
