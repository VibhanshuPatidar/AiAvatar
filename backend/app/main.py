import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from .config import settings
from .schemas import ChatRequest, ChatResponse
from .llm import chat_llm
from .tts import synthesize_speech
from .lipsync import generate_lipsync_json
from .utils import unique_id, ensure_dirs
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Avatar Backend (Python)")

# CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
try:
    ensure_dirs(settings.STATIC_AUDIO_DIR, settings.STATIC_LIPSYNC_DIR)
    logger.info(f"Static directories created: {settings.STATIC_AUDIO_DIR}, {settings.STATIC_LIPSYNC_DIR}")
except Exception as e:
    logger.error(f"Error creating static directories: {e}")

# Serve static files
try:
    static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    logger.info(f"Static files mounted at: {static_path}")
except Exception as e:
    logger.error(f"Error mounting static files: {e}")

SYSTEM_PROMPT = (
    "You are a friendly, virtual avatar for helping the user. "
    "Keep responses short. 1-2 sentences max."
    "Give the output **only** in the following format: "
    "<your response> $$$ <your sentiment>"
    "make sure to use $$$ in your response to seperate the reply from sentiment"
    "make sure that the sentiment is **only** from the list: [smile, funnyFace, sad, surprised, angry, crazy]>"
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "AI Avatar backend is running"}

@app.post("/chat")
async def chat(req: dict):
    """Main chat endpoint that processes user input and returns AI response with audio and lipsync"""
    try:
        # Extract user message
        user_text = req.get("message", "").strip()
        logger.info(f"Received user message: {user_text}")

        if not user_text:
            raise HTTPException(status_code=400, detail="Empty message")

        # Generate LLM response
        try:
            reply = chat_llm(user_text, SYSTEM_PROMPT)
            logger.info(f"LLM reply generated: {reply}")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise HTTPException(status_code=500, detail=f"LLM error: {e}")
        
        reply = reply.strip()
        # read reply as a json format
        if "$$$" in reply:
            reply_text = reply.split("$$$")[0].strip()
            sentiment = reply.split("$$$")[1].strip()
        else:
            sentiment = "smile"
            reply_text = reply
        reply_text = "".join(c for c in reply_text if (ord(c) < 128 or ord(c) == 8217 or ord(c) == 8216))
        sentiment = "".join(c for c in sentiment if ord(c) < 128)
        # keep only alphabets in sentiment
        sentiment = "".join(c for c in sentiment if c.isalpha())
        print(f"Processed reply: {reply_text}, Sentiment: {sentiment}")
        # Delete any previous files in speech and lipsync folders
        for folder in [settings.STATIC_AUDIO_DIR, settings.STATIC_LIPSYNC_DIR]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
        # Generate unique IDs for files
        audio_id = unique_id("speech")
        lipsync_id = unique_id("lipsync")
        reply = reply_text
        # Define file paths
        audio_path = os.path.join(settings.STATIC_AUDIO_DIR, f"{audio_id}.wav")
        lipsync_path = os.path.join(settings.STATIC_LIPSYNC_DIR, f"{lipsync_id}.json")

        logger.info(f"Generated paths - Audio: {audio_path}, Lipsync: {lipsync_path}")

        # Generate speech
        try:
            synthesize_speech(reply, audio_path)
            logger.info(f"Speech synthesized successfully: {audio_path}")
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise HTTPException(status_code=500, detail=f"TTS error: {e}")

        # # Generate lipsync
        try:
            generate_lipsync_json(audio_path, lipsync_path)  # Pass WAV path directly
            logger.info(f"Lipsync generated successfully: {lipsync_path}")
        except Exception as e:
            logger.error(f"LipSync error: {e}")
            raise HTTPException(status_code=500, detail=f"LipSync error: {e}")
        reply = "".join(c for c in reply_text if (ord(c) < 128 or ord(c) == 8217 or ord(c) == 8216))
        # Prepare response
        temp = random.randint(0, 2)
        message_data = {
            "text": reply,
            "audio": f"/static/audio/{audio_id}.wav",
            "lipsync": f"/static/lipsync/{lipsync_id}.json",
            "facialExpression": sentiment,
            "animation": f"Talking_{temp}"
        }
        # # remove any non ascii characters from reply
        # reply = ''.join(c for c in reply if ord(c) < 128)
        # # pick a random number between 0 and 2
        # temp = random.randint(0, 2)
        # message_data = {
        #     "text": reply,
        #     "audio": "/static/audio/speech_20250811153758_87f84d1d.wav",
        #     "lipsync": "/static/lipsync/lipsync_20250811153758_f925eea2.json",
        #     "facialExpression": sentiment,
        #     "animation": f"Talking_{temp}"
        # }
        print(f"Message data prepared: {message_data}")
        return {"messages": [message_data]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
