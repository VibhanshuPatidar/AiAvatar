import json
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

import os
import shutil
import subprocess
import logging

DEVICE_CACHE = {}

SUPPORTED_ACTIONS = {
    "basic_fix",
    "connect_engineer",
    "raise_ticket",
    "close_chat",
    "feedback",
    "__greet__"
}
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)

def memory_file(session_id: str):
    return os.path.join(MEMORY_DIR, f"{session_id}.json")

def load_memory(session_id: str):
    if not os.path.exists(memory_file(session_id)):
        return {
            "phase": "diagnosis",
            "known_facts": {},
            "conversation": []
        }
    with open(memory_file(session_id), "r") as f:
        return json.load(f)

def save_memory(session_id: str, memory: dict):
    with open(memory_file(session_id), "w") as f:
        json.dump(memory, f, indent=2)

def delete_memory(session_id: str):
    path = memory_file(session_id)
    if os.path.exists(path):
        os.remove(path)

@app.get("/device/metrics")
def get_device_metrics(device_id: str = "DEV-001"):
    data = DEVICE_CACHE.get(device_id)
    if not data:
        raise HTTPException(status_code=404, detail="No device metrics available")
    return data

@app.post("/device/telemetry")
def ingest_device_data(payload: dict):
    DEVICE_CACHE[payload["device_id"]] = payload
    return {"status": "ok"}


logger = logging.getLogger(__name__)


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


def is_service_related(user_text: str, memory: dict) -> bool:
    classifier_prompt = f"""
    Classify the user query as SERVICE or NON_SERVICE.
    Conversation so far:
    {json.dumps(memory["conversation"], indent=2)}
    SERVICE means IT support, device issues, performance, errors, tickets or it is related to the conversation happened so far.
    NON_SERVICE means anything which doea not require or cannot be handled by an IT support.

    Reply with only SERVICE or NON_SERVICE.

    Query: {user_text}
    """
    result = chat_llm(user_text, classifier_prompt).strip().upper()
    print(f"Classification result: {result}")
    return "NON_SERVICE" not in result

def convo_summary(memory: dict, phase: str) -> str:
    summary_prompt = f"""
    You are a Digital Service Engineer.
    You solve technical issues for users following a 4 step process: diagnosis, clarification, resolution, and closure.
    1. Diagnosis: Identify the technical issue based on user input and device metrics.
    2. Clarification: Ask targeted questions to gather more information about the issue.
    3. Resolution: Suggest fixes or solutions based on the gathered information.
    4. Closure: Confirm issue resolution and offer further assistance if needed.
    Summarize the following conversation in less than 50 words, focusing on technical issues discussed:

    Conversation:
    {json.dumps(memory["conversation"], indent=2)}

    Also based on the conversation so far, decide whether the next phase is diagnosis, clarification, resolution, or closure.
    diagnosis is when you need more information to identify the issue.
    clarification is when you need to ask targeted questions to gather more information about the issue.
    resolution is when you suggest fixes or solutions based on the gathered information.
    closure is when you confirm issue resolution and offer further assistance if needed.
    Current Phase: {phase}
    
    Give your response **only** in the format:
    <summary> ### <next_phase>
    """
    summary = chat_llm("", summary_prompt).strip().split("###")[0].strip()
    next_phase = chat_llm("", summary_prompt).strip().split("###")[1].strip().lower()
    return summary, next_phase

def build_dynamic_prompt(user_message: str, memory: dict, device_info: dict):
    phase = memory["phase"]

    convo_summary_text, next_phase = convo_summary(memory, phase)
    
    prompt = f"""
        You are a Digital Service Engineer.

        Conversation so far:
        {convo_summary_text}

        Live device metrics (do NOT store these):
        {json.dumps(device_info, indent=2)}

        You solve technical issues for users following a 4 step process: diagnosis, clarification, resolution, and closure.
        1. Diagnosis: Identify the technical issue based on user input and device metrics.
        2. Clarification: Ask targeted questions to gather more information about the issue.
        3. Resolution: Suggest fixes or solutions based on the gathered information.
        4. Closure: Confirm issue resolution and offer further assistance like connect with engineer or raise a ticket if needed.

        Current phase: {next_phase}

        Rules:
        - Behave like a human service engineer
        - Ask clarifying questions BEFORE giving fixes
        - Ask only ONE question at a time
        - If enough information is known, move to resolution
        - If uncertain, suggest connecting to a human engineer
        - Use device data and conversation history to inform your responses, look at the apps open, CPU, RAM, Disk usage to formulate your resolutions
        - dont ask direct questions, frame the questions using the device data provided and give reasoning for asking the question

        Respond naturally and professionally.
        Respond concisely and clearly in less than 50 words.
        If applicable, include suggested actions in the following format, always make sure to add the id and the label in the same way as example:

        OPTIONS:
        - id: connect_engineer $$$ label: Connect to Service Engineer
        - id: raise_ticket $$$ label: Raise a Support Ticket
        - id: basic_fix $$$ label: Try Basic Fix

        "make sure to use $$$ in your response to seperate the reply from sentiment"
        "make sure that the sentiment is **only** from the list: [smile, sad, angry]>"
        "make sure that id is from the supported actions list: connect_engineer, raise_ticket, basic_fix"
        "make sure the final response is in the format:"
        "create only one response"
        Expected response format:
        '<your response with any questions> $$$ <your sentiment> $$$ id: <> $$$ label: <>'

        
        User just said:
        {user_message}
        """
    return prompt


def build_prompt(user_message: str, device_info: dict):
    # device_data = DEVICE_CACHE.get(device_id, {})

    prompt = f"""
    You are a Digital Service Engineer.
    Suggest a fix or solution based on the device metrics provided.
    Live device metrics:
    {json.dumps(device_info, indent=2)}

    Rules:
    - If CPU or RAM > 80%, mention performance impact
    - Suggest fixes conservatively
    - Offer human escalation if uncertain

    User question:
    {user_message}
    
    Respond concisely and clearly in less than 30 words.
    If applicable, include suggested actions in the following format, always make sure to add the id and the label in the same way as example:

    OPTIONS:
    - id: connect_engineer $$$ label: Connect to Service Engineer
    - id: raise_ticket $$$ label: Raise a Support Ticket
    - id: basic_fix $$$ label: Try Basic Fix

   
    "make sure to use $$$ in your response to seperate the reply from sentiment"
    "make sure that the sentiment is **only** from the list: [smile, sad, angry]>"
    "make sure that id is from the supported actions list: connect_engineer, raise_ticket, basic_fix"
    "make sure the final response is in the format:"
    Expected response format:
    '<your response> $$$ <your sentiment> $$$ OPTIONS $$$ id: <> $$$ label: <>'
    """
    return prompt

def handle_action(action_id: str, device_info: dict):
    """
    Deterministic action handling.
    Returns plain text (will be voiced by avatar).
    """

    if action_id == "basic_fix":
        return (
            "I will guide you through a basic performance fix. "
            "Please close unused applications and restart your system."
        )

    if action_id == "connect_engineer":
        return (
            "I am connecting you to a human service engineer. "
            "They will assist you shortly."
        )

    if action_id == "raise_ticket":
        return (
            "I have raised a support ticket with your device details. "
            "You will be notified once an engineer is assigned."
        )
    if action_id == "close_chat":
        
        return (
            "Thanks for chatting. I’ve closed this support session. "
            "Would you like to share quick feedback?"
        )
    if action_id == "feedback":
        
        # add a redirect to feedback form link ##############################################################

        return (
            "Thank you for your feedback! "
            "If you have any more questions or need further assistance, feel free to ask."
        )
    
    if action_id == "__greet__":
        return (
            "Hi Vibhanshu, my name is Ava, "
            "I am your self service assistant."
        )
    raise ValueError(f"Unknown action: {action_id}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "AI Avatar backend is running"}


@app.post("/chat")
async def chat(req: dict):
    session_id = "001"
    memory = load_memory(session_id)

    """Main chat endpoint that processes user input and returns AI response with audio and lipsync"""
    chatclosed = False
    try:
        # Extract user message
        user_text = req.get("message", "").strip().lower()
        # Initial greeting
        

        if user_text == "close_chat":
            chatclosed = True
        device_id = req.get("device_id", "DEV-001")
        user_device_info = DEVICE_CACHE.get(device_id, {})
        if user_text in SUPPORTED_ACTIONS:
            logger.info(f"Handling action: {user_text}")

            try:
                reply_text = handle_action(user_text, user_device_info)
                print("closed chat:", chatclosed)
                sentiment = "smile"
            except Exception as e:
                logger.error(e)
                raise HTTPException(status_code=400, detail=str(e))
        
        logger.info(f"Received user message: {user_text}")
        # prompt = build_prompt(user_text, user_device_info)
        prompt = build_dynamic_prompt(user_text, memory, user_device_info)
        logger.info(f"Constructed prompt: {prompt}")
        if not user_text:
            raise HTTPException(status_code=400, detail="Empty message")
        if user_text not in SUPPORTED_ACTIONS and not is_service_related(user_text, memory):
            reply_text = (
                "I can help only with device and IT support issues. "
                "Please describe a technical problem."
            )
            sentiment = "sad"
            id_response = "None"
            label_response = "None"
            logger.info("Non-service related query detected.")
        # Generate LLM response
        else:
            try:
                if user_text not in SUPPORTED_ACTIONS:
                    memory["conversation"].append({
                        "role": "user",
                        "content": user_text
                    })
                    save_memory(session_id, memory)
                    reply = chat_llm(user_text, prompt)
                    
                else:
                    reply = f"{reply_text} $$$ {sentiment}"
                logger.info(f"LLM reply generated: {reply}")
            except Exception as e:
                logger.error(f"LLM error: {e}")
                raise HTTPException(status_code=500, detail=f"LLM error: {e}")
        # reply = "Hello! How can I assist you today? $$$ smile"  # Temporary hardcoded reply for testing
        # reply = reply.strip()
        # read reply as a json format
            if "$$$" in reply:
                reply_text = reply.split("$$$")[0].strip()
                sentiment = reply.split("$$$")[1].strip()
                try:
                    id_response = reply.split("$$$")[2].strip().replace("id:", "").strip()
                except IndexError:
                    id_response = None
                try:
                    label_response = reply.split("$$$")[3].strip().replace("label:", "").strip()
                except IndexError:
                    label_response = None

            else:
                sentiment = "smile"
                reply_text = reply
        reply_text = "".join(c for c in reply_text if (ord(c) < 128 or ord(c) == 8217 or ord(c) == 8216))
        if "which" in reply_text.lower() or "when" in reply_text.lower():
            memory["phase"] = "clarification"
        elif "I recommend" in reply_text or "Please try" in reply_text:
            memory["phase"] = "resolution"
        memory["conversation"].append({
            "role": "assistant",
            "content": reply_text
        })
        if user_text == "close_chat" or user_text == "feedback":
            delete_memory(session_id)
            memory = {
                "phase": "diagnosis",
                "known_facts": {},
                "conversation": []
            }
        save_memory(session_id, memory)
        if "which" in reply_text.lower() or "when" in reply_text.lower():
            memory["phase"] = "clarification"
        elif "I recommend" in reply_text or "Please try" in reply_text:
            memory["phase"] = "resolution"

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
        if user_text == "__greet__":
            sentiment = "smile"
            id_response = "None"
            label_response = "None"
        # Generate unique IDs for files
        audio_id = unique_id("speech")
        lipsync_id = unique_id("lipsync")
        reply = reply_text.split('OPTIONS:')[0].strip()
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

        # check if audio path exists
        if not os.path.exists(audio_path):
            print(f"Audio directory does not exist: {settings.STATIC_AUDIO_DIR}")
        else:
            print(f"Audio directory exists: {settings.STATIC_AUDIO_DIR}")

        # # convert audio file from wav to mp3
        # try:
        #     mp3_path = convert_wav_to_mp3(audio_path)
        #     logger.info(f"Audio converted successfully: {mp3_path}")
        # except Exception as e:
        #     logger.error(f"Audio conversion error: {e}")
        #     raise HTTPException(status_code=500, detail=f"Audio conversion error: {e}")
        # print(id_response, label_response)
        # print(f"chatclosed status: {chatclosed}")
        if chatclosed==True:
            id_response = "None"
            label_response = "None"
        print(id_response, label_response)
        # Prepare response
        temp = random.randint(0, 2)
        message_data = {
            "text": reply,
            "audio": f"/static/audio/{audio_id}.wav",
            # "audio": f"{mp3_path.replace(os.path.abspath(static_path), '/static').replace(os.sep, '/')}",
            "lipsync": f"/static/lipsync/{lipsync_id}.json",
            "facialExpression": sentiment,
            "animation": f"Talking_{temp}",
            "id_response": f"{id_response}",
            "label_response": f"{label_response}"
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