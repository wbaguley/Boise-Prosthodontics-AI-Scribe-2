from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import torch
import numpy as np
import os
import tempfile
import logging
from datetime import datetime
import asyncio
import json
from pathlib import Path
import subprocess
import requests

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename='logs/scribe_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Boise Prosthodontics AI Scribe")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

# Initialize models (lazy loading for memory efficiency)
print("Loading Whisper model...")
try:
    model = WhisperModel('base', device='cuda' if torch.cuda.is_available() else 'cpu', compute_type='int8')
    print("✅ Whisper model loaded successfully")
except Exception as e:
    print(f"⚠️ Could not load Whisper model: {e}")
    print("Continuing with mock transcription...")
    model = None

# Simplified - no diarization or TTS for now
print("✅ Simplified backend ready (no diarization/TTS)")

# Ensure models directory exists
Path("models").mkdir(exist_ok=True)

async def safe_send_json(websocket: WebSocket, payload: dict):
    """Send JSON over websocket and swallow errors if client disconnected."""
    try:
        await websocket.send_json(payload)
        return True
    except Exception:
        logging.warning(f"WebSocket closed while trying to send: {payload}")
        return False

def convert_webm_to_wav(webm_data, session_id=None):
    """Convert WebM audio to WAV format using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
        webm_path = webm_file.name
        webm_file.write(webm_data)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
        wav_path = wav_file.name
    
    # Try multiple ffmpeg strategies to handle codec/container variances
    ffmpeg_cmds = [
        ['ffmpeg', '-y', '-i', webm_path, '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path],
        ['ffmpeg', '-y', '-f', 'webm', '-i', webm_path, '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path],
        ['ffmpeg', '-y', '-i', webm_path, '-map', '0:a', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path]
    ]

    for cmd in ffmpeg_cmds:
        try:
            proc = subprocess.run(cmd, check=True, capture_output=True)
            # success
            try:
                os.remove(webm_path)
            except Exception:
                pass
            return wav_path
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='ignore') if hasattr(e, 'stderr') and e.stderr else ''
            stdout = e.stdout.decode('utf-8', errors='ignore') if hasattr(e, 'stdout') and e.stdout else ''
            logging.warning(f"FFmpeg attempt failed (cmd={' '.join(cmd)}); stdout={stdout}; stderr={stderr}")

    # All attempts failed
    try:
        os.remove(webm_path)
    except Exception:
        pass
    return None

def format_soap_note(transcript):
    """Format transcript into SOAP note using Ollama or fallback."""
    soap_prompt = f"""Convert this medical conversation transcript into a SOAP note format.
    
Transcript:
{transcript}

Create a structured SOAP note with:
- SUBJECTIVE: Patient's complaints and symptoms
- OBJECTIVE: Clinical findings and observations
- ASSESSMENT: Clinical assessment and diagnosis
- PLAN: Treatment plan and follow-up

Format it clearly for copy-paste into Dentrix. Be concise but thorough."""
    
    try:
        # Try to connect to Ollama
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "prompt": soap_prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'Error generating SOAP note')
        else:
            raise Exception(f"Ollama returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        logging.error(f"Could not connect to Ollama at {OLLAMA_HOST}")
        # Fallback formatting
        return f"""SOAP Note (Auto-formatted)

SUBJECTIVE:
{transcript}

OBJECTIVE:
[Clinical findings to be filled by practitioner]

ASSESSMENT:
[Diagnosis and clinical assessment to be filled by practitioner]

PLAN:
[Treatment plan and follow-up to be filled by practitioner]

[Please review and edit before saving to Dentrix]"""
    except Exception as e:
        logging.error(f"Ollama error: {e}")
        return f"SOAP Note (Auto-formatted)\n\n{transcript}\n\n[Please review and edit before saving to Dentrix]"

@app.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()
    audio_chunks = []
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = None
    
    try:
        # Receive audio chunks
        while True:
            data = await websocket.receive()

            if 'text' in data and data['text'] == 'END':
                break
            elif 'bytes' in data:
                audio_chunks.append(data['bytes'])

        if not audio_chunks:
            await safe_send_json(websocket, {"error": "No audio received"})
            return

        logging.info(f"Session {session_id}: Processing {len(audio_chunks)} audio chunks")

        # Combine chunks
        combined_audio = b''.join(audio_chunks)

        # Convert WebM to WAV
        await safe_send_json(websocket, {"status": "Converting audio..."})
        audio_path = convert_webm_to_wav(combined_audio, session_id=session_id)
        if audio_path is None:
            await safe_send_json(websocket, {"error": "Audio conversion failed", "status": "Complete"})
            return

        # Transcribe audio
        await safe_send_json(websocket, {"status": "Transcribing..."})

        if model:
            segments, info = model.transcribe(audio_path, beam_size=5)
            segments_list = list(segments)

            if not segments_list:
                await safe_send_json(websocket, {
                    "error": "No speech detected in audio",
                    "status": "Complete"
                })
                return

            # Simple alternating speaker assignment (no diarization)
            diarized_transcript = []
            for i, seg in enumerate(segments_list):
                speaker = "Doctor" if i % 2 == 0 else "Patient"
                line = f"{speaker}: {seg.text.strip()}"
                diarized_transcript.append(line)

            full_transcript = '\n'.join(diarized_transcript)
        else:
            # Mock transcription for testing
            full_transcript = """Doctor: Hello, how are you feeling today?
Patient: I've been having some pain in my upper left molar.
Doctor: When did this pain start?
Patient: About three days ago, it's been getting worse.
Doctor: I see. Let me take a look at that tooth."""

        # Send transcript
        await safe_send_json(websocket, {
            "transcript": full_transcript,
            "status": "Generating SOAP note..."
        })

        # Generate SOAP note
        soap_note = format_soap_note(full_transcript)

        # Send final SOAP note
        await safe_send_json(websocket, {
            "soap": soap_note,
            "transcript": full_transcript,
            "status": "Complete"
        })

        # Log session
        logging.info(f"Session {session_id}: Completed successfully")
        logging.info(f"Transcript length: {len(full_transcript)} chars")
        logging.info(f"SOAP note length: {len(soap_note)} chars")
        
    except WebSocketDisconnect:
        logging.warning(f"Session {session_id}: WebSocket disconnected")
    except Exception as e:
        logging.error(f"Session {session_id}: Error - {str(e)}")
        try:
            await safe_send_json(websocket, {"error": str(e)})
        except Exception:
            logging.warning("WebSocket closed while trying to send error")
    finally:
        # Ensure cleanup
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass

@app.get("/")
async def root():
    return {
        "service": "Boise Prosthodontics AI Scribe",
        "status": "running",
        "models": {
            "whisper": "base" if model else "not available",
            "diarization": "simplified (alternating speakers)",
            "llm": "llama3 (with fallback)",
            "tts": "not available"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("🏥 Starting Boise Prosthodontics AI Scribe Backend...")
    print("📍 WebSocket endpoint: ws://localhost:4001/ws/audio")
    print("🌐 Health check: http://localhost:4001/health")
    uvicorn.run(app, host="0.0.0.0", port=4001)
