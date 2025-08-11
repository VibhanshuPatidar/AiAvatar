import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        # LLM Configuration
        self.OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gemma2:4b")  # Fixed model name

        # TTS Configuration
        self.TTS_PROVIDER = os.getenv("TTS_PROVIDER", "piper").lower()
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        self.ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")

        # Piper Configuration
        self.PIPER_EXECUTABLE = os.getenv("PIPER_EXECUTABLE", "piper")
        self.PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")

        # Rhubarb Configuration
        self.RHUBARB_PATH = os.getenv("RHUBARB_PATH", "./bin/rhubarb")

        # Directory Configuration
        base_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(base_dir, "..", "static")
        self.STATIC_AUDIO_DIR = os.path.abspath(os.path.join(static_dir, "audio"))
        self.STATIC_LIPSYNC_DIR = os.path.abspath(os.path.join(static_dir, "lipsync"))

        # Server Configuration
        self.HOST = os.getenv("HOST", "0.0.0.0")
        self.PORT = int(os.getenv("PORT", "8000"))

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate configuration and log warnings for missing components"""
        # Check Ollama
        try:
            import requests
            response = requests.get(f"{self.OLLAMA_HOST}/api/version", timeout=5)
            if response.status_code == 200:
                logger.info("Ollama connection successful")
            else:
                logger.warning("Ollama server not responding properly")
        except Exception as e:
            logger.warning(f"Cannot connect to Ollama: {e}")

        # Check TTS Provider
        if self.TTS_PROVIDER == "elevenlabs":
            if not self.ELEVENLABS_API_KEY:
                logger.warning("ElevenLabs API key not provided")
        elif self.TTS_PROVIDER == "piper":
            logger.info("Piper TTS configured - ensure piper is installed")

        # Check Rhubarb
        if not os.path.exists(self.RHUBARB_PATH):
            logger.warning(f"Rhubarb not found at {self.RHUBARB_PATH} - will use dummy lipsync")

settings = Settings()
