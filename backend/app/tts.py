import os
import subprocess
import tempfile
import requests
from pydub import AudioSegment
from .config import settings

def synthesize_speech(text: str, out_wav_path: str) -> None:
    provider = settings.TTS_PROVIDER.lower()
    print(f"Starting TTS synthesis with provider: {provider}")
    if provider == "elevenlabs":
        print(f"ElevenLabs TTS started")
        _synthesize_elevenlabs(text, out_wav_path)
        print(f"ElevenLabs TTS completed: {out_wav_path}")
    elif provider == "piper":
        _synthesize_piper(text, out_wav_path)
    elif provider == "none":
        # Create silent WAV as placeholder
        silence = AudioSegment.silent(duration=2000)  # 2 seconds
        silence.export(out_wav_path, format="wav")
    else:
        print(f"Unsupported TTS provider: {provider}")
        raise RuntimeError(f"Unsupported TTS_PROVIDER: {provider}")

def _synthesize_elevenlabs(text: str, out_wav_path: str) -> None:
    api_key = settings.ELEVENLABS_API_KEY
    voice_id = settings.ELEVENLABS_VOICE_ID
    if not api_key or not voice_id:
        raise RuntimeError("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID must be set")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
    }

    # Create a closed temp file path (Windows-friendly)
    tmp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    mp3_path = tmp_mp3.name
    tmp_mp3.close()

    try:
        # Download streaming MP3 fully to mp3_path
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(mp3_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        # Verify non-empty file (guard against server anomalies)
        if os.path.getsize(mp3_path) == 0:
            raise RuntimeError("Downloaded MP3 is empty")

        # Decode MP3 -> WAV
        audio = AudioSegment.from_file(mp3_path, format="mp3")
        audio.export(out_wav_path, format="wav")

    finally:
        # Clean up temp file
        if os.path.exists(mp3_path):
            os.unlink(mp3_path)

def _synthesize_piper(text: str, out_wav_path: str) -> None:
    piper = settings.PIPER_EXECUTABLE
    voice = settings.PIPER_VOICE
    if not piper or not voice:
        raise RuntimeError("PIPER_EXECUTABLE and PIPER_VOICE must be set")

    cmd = [piper, "-m", voice, "-f", out_wav_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(text, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Piper failed: {stderr}")
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("Piper timed out")
