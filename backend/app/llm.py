import requests
from .config import settings
from safechain.lcel import model
from safechain.prompts import ValidPromptTemplate
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv("/Users/vpatid/Library/CloudStorage/OneDrive-AmericanExpress/Desktop/AiAvatar-main/backend/.env"))

def invoke_llm(advanced_prompt):
    prompt = ValidPromptTemplate(template="{advanced_prompt}")
    print("prompt: ", prompt)
    chain = prompt | model()
    # out = chain.invoke({"advanced_prompt":  advanced_prompt})
    print("chain: ", chain)
    out = chain.invoke({"advanced_prompt":  advanced_prompt})
    return out

def chat_llm(user_text: str, system_prompt: str = "") -> str:
    
    # url = f"{settings.OLLAMA_HOST}/api/generate"
    # Using /api/generate with prompt; for chat, you can also use /api/chat.
    prompt = (system_prompt if system_prompt else "") + f"  User: {user_text}"
    # payload = {
    #     "model": settings.LLM_MODEL,
    #     "prompt": prompt,
    #     "stream": False,
    #     "options": {
    #         "temperature": 0.7,
    #     }
    # }
    print(f"Calling LLM with prompt: {prompt}")
    resp = invoke_llm(prompt).content
    print(f"LLM response: {resp}")
    # resp.raise_for_status()
    # data = resp.json()
    # return resp.get("response", "").strip()
    return resp.strip()
    # return "LLM response"

if __name__ == "__main__":
    test_prompt = "Explain the theory of relativity in simple terms."
    response = chat_llm(test_prompt, "You are a helpful assistant.")
    print(f"LLM Test Response: {response}")
