from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import whisper
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
from typing import Optional, List, Dict
import wave
import io
from pydantic import BaseModel

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename='logs/scribe_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Boise Prosthodontics AI Scribe")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
MODEL_SIZE = os.getenv('WHISPER_MODEL', 'base')

# Prosthodontics terminology for better recognition
PROSTHODONTICS_TERMS = [
    "abutment", "pontic", "crown", "bridge", "veneer", "implant",
    "occlusion", "TMJ", "bruxism", "edentulous", "denture", "partial",
    "fixed prosthesis", "removable prosthesis", "impression", "articulator",
    "centric relation", "vertical dimension", "interocclusal", "maxillary",
    "mandibular", "zirconia", "porcelain", "PFM", "all-ceramic", "CAD/CAM",
    "bite registration", "provisional", "temporization", "cement", "bond",
    "margin", "chamfer", "shoulder", "preparation", "undercut", "path of insertion",
    "retention", "resistance", "ferrule", "post", "core", "buildup",
    "periodontal", "gingival", "biological width", "emergence profile",
    "tooth shade", "stump shade", "try-in", "glazing", "characterization"
]

class TranscriptionSession:
    def __init__(self):
        self.audio_buffer = []
        self.transcript_buffer = []
        self.speaker_history = []
        self.context = []
        
class AIScribeEngine:
    def __init__(self):
        self.whisper_model = None
        self.sessions = {}
        self.load_models()
    
    def load_models(self):
        """Load Whisper model with error handling"""
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading Whisper model ({MODEL_SIZE}) on {device}...")
            self.whisper_model = whisper.load_model(MODEL_SIZE, device=device)
            
            # Add custom vocabulary for better prosthodontics recognition
            print("✅ Whisper model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            print(f"⚠️ Whisper model failed to load: {e}")
    
    def convert_audio(self, audio_data: bytes, format: str = "webm") -> Optional[str]:
        """Convert audio to WAV format for processing"""
        try:
            # Save input audio
            with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as f:
                f.write(audio_data)
                input_path = f.name
            
            # Create output path
            output_path = tempfile.mktemp(suffix='.wav')
            
            # Convert using ffmpeg
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Cleanup input
            os.unlink(input_path)
            
            if result.returncode == 0:
                return output_path
            else:
                logging.error(f"FFmpeg conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Audio conversion error: {e}")
            return None
    
    def transcribe_audio(self, audio_path: str, session_id: str) -> Dict:
        """Transcribe audio with speaker detection"""
        try:
            if not self.whisper_model:
                return {"error": "Whisper model not loaded"}
            
            # Transcribe with word timestamps for better diarization
            result = self.whisper_model.transcribe(
                audio_path,
                language="en",
                word_timestamps=True,
                initial_prompt="This is a dental consultation between a prosthodontist and patient discussing dental procedures, implants, crowns, and oral health."
            )
            
            # Process segments with simple speaker diarization
            segments = []
            current_speaker = "Doctor"
            
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if not text:
                    continue
                
                # Simple heuristic for speaker change detection
                # (In production, you'd use pyannote or similar)
                if any(phrase in text.lower() for phrase in ["how are you", "what brings you", "let me examine", "i can see"]):
                    current_speaker = "Doctor"
                elif any(phrase in text.lower() for phrase in ["i have", "it hurts", "i feel", "when i"]):
                    current_speaker = "Patient"
                
                segments.append({
                    "speaker": current_speaker,
                    "text": text,
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0)
                })
                
                # Toggle speaker for next segment (simplified)
                current_speaker = "Patient" if current_speaker == "Doctor" else "Doctor"
            
            return {
                "segments": segments,
                "full_text": result.get("text", ""),
                "language": result.get("language", "en")
            }
            
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            return {"error": str(e)}
    
    def generate_soap_note(self, transcript: str, context: str = "") -> str:
        """Generate SOAP note using Llama via Ollama"""
        
        # Enhanced prompt with prosthodontics context
        prompt = f"""You are an expert prosthodontist assistant. Convert this dental consultation transcript into a structured SOAP note.

IMPORTANT CONTEXT: This is a prosthodontics practice specializing in:
- Crown and bridge work
- Dental implants and abutments  
- Complete and partial dentures
- TMJ disorders
- Complex restorative cases
- Aesthetic dentistry

Previous context (if any): {context}

Current Transcript:
{transcript}

Create a detailed SOAP note following this exact format:

SUBJECTIVE:
- Chief Complaint: [specific reason for visit]
- History of Present Illness: [onset, duration, severity, location, quality of symptoms]
- Dental History: [relevant previous treatments]
- Medical History: [if mentioned]
- Current Medications: [if mentioned]

OBJECTIVE:
- Extraoral Exam: [if performed]
- Intraoral Exam: [specific teeth, soft tissue findings]
- Radiographic Findings: [if X-rays mentioned]
- Existing Restorations: [crowns, bridges, implants noted]
- Periodontal Status: [if assessed]
- Occlusion: [if evaluated]

ASSESSMENT:
- Primary Diagnosis: [use proper dental terminology and tooth numbers]
- Differential Diagnosis: [if applicable]
- Prognosis: [if discussed]

PLAN:
- Immediate Treatment: [today's procedures]
- Future Treatment: [planned procedures with timeline]
- Medications: [prescribed or recommended]
- Patient Education: [home care instructions given]
- Next Appointment: [follow-up schedule]

Use standard tooth numbering (1-32) and proper prosthodontic terminology. Be specific and clinically accurate."""

        try:
            # Call Ollama API
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent medical notes
                        "top_p": 0.9,
                        "num_ctx": 4096  # Larger context window
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                soap_note = result.get('response', '')
                
                # Post-process to ensure format
                if not soap_note.startswith("SUBJECTIVE:"):
                    soap_note = "SUBJECTIVE:\n" + soap_note
                    
                return soap_note
            else:
                raise Exception(f"Ollama returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logging.error(f"Cannot connect to Ollama at {OLLAMA_HOST}")
            # Fallback template
            return self.generate_fallback_soap(transcript)
        except Exception as e:
            logging.error(f"SOAP generation error: {e}")
            return self.generate_fallback_soap(transcript)
    
    def generate_fallback_soap(self, transcript: str) -> str:
        """Generate a structured template when AI is unavailable"""
        return f"""SOAP Note - Manual Review Required

SUBJECTIVE:
Chief Complaint: [To be extracted from transcript]
History: {transcript[:200]}...

OBJECTIVE:
Clinical Findings: [Requires manual entry]
- Teeth examined: 
- Soft tissue status:
- Existing restorations:

ASSESSMENT:
[Requires clinical interpretation]

PLAN:
[Treatment plan to be determined]

---
Full Transcript for Reference:
{transcript}

⚠️ Note: AI processing unavailable. Please review and complete manually."""

# Initialize the engine
engine = AIScribeEngine()

@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time audio streaming and transcription"""
    await websocket.accept()
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = TranscriptionSession()
    engine.sessions[session_id] = session
    
    audio_chunks = []
    processing = False
    
    try:
        await websocket.send_json({
            "status": "Connected",
            "session_id": session_id,
            "message": "Ready to receive audio"
        })
        
        while True:
            # Receive data
            data = await websocket.receive()
            
            # Handle different message types
            if "text" in data:
                message = data["text"]
                
                if message == "END":
                    # Process accumulated audio
                    processing = True
                    await process_audio_chunks(
                        websocket, audio_chunks, session_id, session
                    )
                    audio_chunks = []
                    processing = False
                    
                elif message.startswith("CORRECT:"):
                    # Handle corrections
                    correction = message[8:]
                    await handle_correction(websocket, session, correction)
                    
                elif message == "CONTEXT":
                    # Send current context
                    await websocket.send_json({
                        "context": session.context,
                        "transcript": "\n".join(session.transcript_buffer)
                    })
                    
            elif "bytes" in data:
                # Accumulate audio chunks
                audio_chunks.append(data["bytes"])
                
                # Send periodic status updates
                if len(audio_chunks) % 10 == 0:
                    await websocket.send_json({
                        "status": "Recording",
                        "chunks_received": len(audio_chunks)
                    })
    
    except WebSocketDisconnect:
        logging.info(f"Session {session_id} disconnected")
    except Exception as e:
        logging.error(f"WebSocket error in session {session_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        # Cleanup
        if session_id in engine.sessions:
            del engine.sessions[session_id]

async def process_audio_chunks(
    websocket: WebSocket,
    audio_chunks: List[bytes],
    session_id: str,
    session: TranscriptionSession
):
    """Process accumulated audio chunks"""
    
    if not audio_chunks:
        await websocket.send_json({"error": "No audio data received"})
        return
    
    try:
        # Combine audio chunks
        await websocket.send_json({"status": "Processing audio..."})
        combined_audio = b''.join(audio_chunks)
        
        # Convert to WAV
        audio_path = engine.convert_audio(combined_audio, format="webm")
        if not audio_path:
            await websocket.send_json({"error": "Audio conversion failed"})
            return
        
        # Transcribe
        await websocket.send_json({"status": "Transcribing..."})
        transcription = engine.transcribe_audio(audio_path, session_id)
        
        if "error" in transcription:
            await websocket.send_json({
                "error": f"Transcription failed: {transcription['error']}"
            })
            return
        
        # Format transcript with speakers
        formatted_transcript = []
        for segment in transcription.get("segments", []):
            line = f"{segment['speaker']}: {segment['text']}"
            formatted_transcript.append(line)
            session.transcript_buffer.append(line)
        
        full_transcript = "\n".join(formatted_transcript)
        
        # Send transcript
        await websocket.send_json({
            "transcript": full_transcript,
            "status": "Generating SOAP note..."
        })
        
        # Generate SOAP note with context
        context = "\n".join(session.context[-5:]) if session.context else ""
        soap_note = engine.generate_soap_note(full_transcript, context)
        
        # Add to context for future reference
        session.context.append(full_transcript)
        
        # Send final results
        await websocket.send_json({
            "transcript": full_transcript,
            "soap": soap_note,
            "status": "Complete",
            "session_id": session_id
        })
        
        # Cleanup
        os.unlink(audio_path)
        
        # Log session
        logging.info(f"Session {session_id} completed successfully")
        
    except Exception as e:
        logging.error(f"Processing error: {e}")
        await websocket.send_json({
            "error": str(e),
            "status": "Error"
        })

async def handle_correction(
    websocket: WebSocket,
    session: TranscriptionSession,
    correction: str
):
    """Handle user corrections to improve accuracy"""
    
    # Add correction to context
    session.context.append(f"CORRECTION: {correction}")
    
    # Regenerate SOAP with correction
    all_transcript = "\n".join(session.transcript_buffer)
    updated_transcript = f"{all_transcript}\n\nCorrection: {correction}"
    
    await websocket.send_json({"status": "Updating SOAP note..."})
    
    updated_soap = engine.generate_soap_note(
        updated_transcript,
        context="\n".join(session.context)
    )
    
    await websocket.send_json({
        "soap": updated_soap,
        "status": "Updated",
        "message": "SOAP note updated with correction"
    })

@app.get("/")
async def root():
    """Service information endpoint"""
    return {
        "service": "Boise Prosthodontics AI Scribe",
        "version": "2.0.0",
        "status": "operational",
        "features": {
            "transcription": "Whisper AI",
            "llm": "Llama 3 via Ollama",
            "specialization": "Prosthodontics",
            "realtime": True,
            "corrections": True
        },
        "models_loaded": {
            "whisper": engine.whisper_model is not None,
            "ollama": OLLAMA_HOST
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check Whisper
    whisper_status = "healthy" if engine.whisper_model else "not loaded"
    
    # Check Ollama
    ollama_status = "unknown"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy" if whisper_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "whisper": whisper_status,
            "ollama": ollama_status
        }
    }

@app.post("/api/train/vocabulary")
async def add_vocabulary(terms: List[str]):
    """Add custom prosthodontics terms for better recognition"""
    global PROSTHODONTICS_TERMS
    PROSTHODONTICS_TERMS.extend(terms)
    return {"message": f"Added {len(terms)} terms to vocabulary"}

if __name__ == "__main__":
    import uvicorn
    print("🦷 Starting Boise Prosthodontics AI Scribe...")
    print(f"📍 WebSocket: ws://localhost:3051/ws/audio")
    print(f"🧠 Ollama: {OLLAMA_HOST}")
    uvicorn.run(app, host="0.0.0.0", port=3051)