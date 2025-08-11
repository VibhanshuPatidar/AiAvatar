import json
import os
import subprocess
import tempfile
from pydub import AudioSegment
from .config import settings
import logging

logger = logging.getLogger(__name__)

def generate_lipsync_json(wav_path: str, out_json_path: str) -> None:
    """
    Uses Rhubarb CLI to produce JSON lip sync from audio.
    Takes WAV input directly and generates lipsync JSON.
    """
    rhubarb = settings.RHUBARB_PATH

    # Check if rhubarb executable exists
    if not os.path.isfile(rhubarb):
        logger.error(f"Rhubarb binary not found at {rhubarb}")
        # Create dummy lipsync data if rhubarb is not available
        create_dummy_lipsync(out_json_path)
        return

    try:
        # Verify input file exists and is WAV
        if not os.path.exists(wav_path):
            raise RuntimeError(f"Input audio file not found: {wav_path}")

        # Ensure input is WAV format
        if not wav_path.lower().endswith('.wav'):
            logger.warning(f"Input file {wav_path} is not WAV, converting...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                audio = AudioSegment.from_file(wav_path)
                audio.export(temp_wav.name, format="wav")
                wav_path = temp_wav.name

        # Run Rhubarb
        cmd = [rhubarb, "-f", "json", "-o", out_json_path, wav_path]
        logger.info(f"Running Rhubarb command: {' '.join(cmd)}")

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if proc.returncode != 0:
            logger.error(f"Rhubarb failed with return code {proc.returncode}: {proc.stderr}")
            create_dummy_lipsync(out_json_path)
            return

        # Validate JSON has mouthCues
        with open(out_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "mouthCues" not in data:
            logger.warning("Rhubarb output missing 'mouthCues', creating dummy data")
            create_dummy_lipsync(out_json_path)
            return

        logger.info(f"Lipsync generated successfully with {len(data['mouthCues'])} mouth cues")

    except subprocess.TimeoutExpired:
        logger.error("Rhubarb execution timed out")
        create_dummy_lipsync(out_json_path)
    except Exception as e:
        logger.error(f"Error generating lipsync: {e}")
        create_dummy_lipsync(out_json_path)

def create_dummy_lipsync(out_json_path: str) -> None:
    """Create dummy lipsync data as fallback"""
    dummy_data = {
        "mouthCues": [
            {"start": 0.0, "end": 0.5, "value": "A"},
            {"start": 0.5, "end": 1.0, "value": "B"},
            {"start": 1.0, "end": 1.5, "value": "C"},
        ],
        "metadata": {
            "soundFile": "",
            "duration": 2.0
        }
    }

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, indent=2)

    logger.info(f"Created dummy lipsync data at {out_json_path}")
