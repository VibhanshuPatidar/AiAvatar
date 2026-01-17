import os
import requests
from .config import settings

def chat_llm(user_text: str, system_prompt: str = "") -> str:
    """
    Unified LLM client for Ollama, OpenAI, Perplexity, and Gemini.
    Select provider via .env setting: LLM_PROVIDER = ollama|openai|perplexity|gemini
    """

    provider = getattr(settings, "LLM_PROVIDER", "ollama").lower()
    print(f"[LLM] Using provider: {provider}")
    # System + user prompt formatting
    prompt = (system_prompt if system_prompt else "") + f"\nUser: {user_text}"

    if provider == "ollama":
        # ----------------- OLLAMA -----------------
        model_name = getattr(settings, "LLM_MODEL", "gemma3:4b")
        url = f"{settings.OLLAMA_HOST}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096,
            },
        }
        print(f"[Ollama] Calling {model_name} with payload: {payload}")
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    elif provider == "openai":
        # ----------------- OPENAI -----------------
        api_key = os.getenv("OPENAI_API_KEY")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_text}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        print(f"[OpenAI] Payload: {payload}")
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    elif provider == "perplexity":
        # ----------------- PERPLEXITY -----------------
        api_key = os.getenv("PERPLEXITY_API_KEY")
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": getattr(settings, "PERPLEXITY_MODEL", "sonar-small-chat"),
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_text}],
            "temperature": 0.7,
        }
        print(f"[Perplexity] Payload: {payload}")
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    elif provider == "gemini":
        # ----------------- GEMINI -----------------
        api_key = os.getenv("GEMINI_API_KEY")
        model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"role": "system", "parts": [{"text": system_prompt}]},
                {"role": "user", "parts": [{"text": user_text}]},
            ]
        }
        print(f"[Gemini] Payload: {payload}")
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
        return ""

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
