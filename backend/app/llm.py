import requests
from .config import settings

def chat_llm(user_text: str, system_prompt: str = "") -> str:
    """
    Calls local Ollama model (Gemma 4B) for chat completion.
    Requires `ollama run <model>` pre-pulled and Ollama server running.
    """
    url = f"{settings.OLLAMA_HOST}/api/generate"
    # Using /api/generate with prompt; for chat, you can also use /api/chat.
    prompt = (system_prompt + "\n\n" if system_prompt else "") + f"User: {user_text}\nAssistant:"
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
        }
    }
    print(f"Calling LLM with payload: {payload}")
    # resp = requests.post(url, json=payload, timeout=120)
    # print(f"LLM response: {resp.text}")
    # resp.raise_for_status()
    # data = resp.json()
    # return data.get("response", "").strip()
    return "LLM response"
