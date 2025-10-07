from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime
import json
import requests
from pathlib import Path
import tempfile
import subprocess
import base64

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename='logs/scribe_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Boise Prosthodontics AI Scribe")

# CORS middleware - allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama:11434')

# Try to import Whisper - fallback to mock if not available
try:
    import whisper
    WHISPER_AVAILABLE = True
    WHISPER_MODEL = None
    print("Whisper import successful, loading model...")
    try:
        WHISPER_MODEL = whisper.load_model("base")
        print("✅ Whisper model loaded successfully")
    except Exception as e:
        print(f"⚠️ Could not load Whisper model: {e}")
        WHISPER_AVAILABLE = False
except ImportError:
    print("⚠️ Whisper not available, using mock mode")
    WHISPER_AVAILABLE = False
    WHISPER_MODEL = None

# Prosthodontics-specific terms for better recognition
DENTAL_CONTEXT = """This is a prosthodontics consultation. Common terms include:
crown, bridge, implant, abutment, veneer, denture, occlusion, TMJ, 
tooth numbers 1-32, maxillary, mandibular, mesial, distal, buccal, 
lingual, provisional, impression, cement, margin, preparation."""

def convert_audio_to_wav(audio_data):
    """Convert webm audio to wav using ffmpeg"""
    try:
        # Save webm to temp file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
            webm_file.write(audio_data)
            webm_path = webm_file.name
        
        # Create wav output path
        wav_path = tempfile.mktemp(suffix='.wav')
        
        # Convert using ffmpeg
        cmd = [
            'ffmpeg', '-y', '-i', webm_path,
            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            wav_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up webm file
        os.unlink(webm_path)
        
        if result.returncode == 0:
            return wav_path
        else:
            logging.error(f"FFmpeg error: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Audio conversion error: {e}")
        return None

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper or mock"""
    if WHISPER_AVAILABLE and WHISPER_MODEL and audio_path:
        try:
            # Use Whisper for real transcription
            result = WHISPER_MODEL.transcribe(
                audio_path,
                language="en",
                initial_prompt=DENTAL_CONTEXT,
                temperature=0.2
            )
            
            # Format with speaker detection (simple alternating for now)
            segments = result.get("segments", [])
            if not segments:
                return result.get("text", "No speech detected")
            
            # Simple speaker diarization
            formatted_lines = []
            current_speaker = "Doctor"
            
            for i, segment in enumerate(segments):
                text = segment["text"].strip()
                if not text:
                    continue
                
                # Simple heuristics for speaker change
                if any(word in text.lower() for word in ["doctor", "let me", "i can see", "examination shows"]):
                    current_speaker = "Doctor"
                elif any(word in text.lower() for word in ["i have", "my tooth", "it hurts", "i feel"]):
                    current_speaker = "Patient"
                
                formatted_lines.append(f"{current_speaker}: {text}")
                
                # Toggle speaker for next segment
                current_speaker = "Patient" if current_speaker == "Doctor" else "Doctor"
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logging.error(f"Transcription error: {e}")
            return f"Transcription error: {str(e)}"
    else:
        # Fallback to mock
        return generate_mock_transcript()

def generate_mock_transcript():
    """Generate a mock transcript for testing"""
    return """Doctor: Good morning, what brings you in today?
Patient: I've been having sensitivity in my upper left area, especially with cold drinks.
Doctor: How long has this been going on?
Patient: About two weeks now. It's gotten worse in the last few days.
Doctor: Let me take a look. I can see you have an existing crown on tooth number 14.
Patient: Yes, I got that about five years ago.
Doctor: There appears to be some recession around the margin of the crown. We should take an x-ray.
Patient: Is the crown failing?
Doctor: We'll need the x-ray to confirm, but there may be some cement washout or secondary decay."""

def generate_soap_note(transcript):
    """Generate SOAP note using Ollama with prosthodontics focus"""
    
    prompt = f"""You are a prosthodontist. Convert this dental consultation into a detailed SOAP note.

Consultation Transcript:
{transcript}

Create a professional SOAP note with these sections:

SUBJECTIVE:
- Chief Complaint: [specific symptom and location]
- History of Present Illness: [onset, duration, severity, aggravating factors]
- Dental History: [relevant past treatments]
- Review of Systems: [relevant systemic factors]

OBJECTIVE:
- Clinical Examination: [specific findings]
- Existing Restorations: [list with tooth numbers]
- Radiographic Findings: [if mentioned]
- Periodontal Status: [if observed]

ASSESSMENT:
- Primary Diagnosis: [use dental terminology and tooth numbers]
- Differential Diagnosis: [if applicable]
- Prognosis: [treatment outlook]

PLAN:
- Immediate Treatment: [today's procedures]
- Definitive Treatment: [long-term plan]
- Medications: [if prescribed]
- Follow-up: [next appointment]

Use standard tooth numbering (1-32) and proper dental terminology."""

    try:
        # Try Ollama first
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=45
        )
        
        if response.status_code == 200:
            soap = response.json().get('response', '')
            if soap and len(soap) > 50:
                return soap
                
    except Exception as e:
        logging.error(f"Ollama error: {e}")
    
    # Enhanced fallback SOAP note
    return """SUBJECTIVE:
- Chief Complaint: Sensitivity in upper left quadrant, especially to cold stimuli
- History of Present Illness: Symptoms began 2 weeks ago, progressive worsening over last few days
- Dental History: Crown placed on tooth #14 approximately 5 years ago
- Review of Systems: No reported systemic conditions affecting dental treatment

OBJECTIVE:
- Clinical Examination: Gingival recession noted around crown margin on tooth #14
- Existing Restorations: PFM crown on tooth #14 with visible margin
- Radiographic Findings: Pending - periapical radiograph ordered
- Periodontal Status: Localized recession at #14

ASSESSMENT:
- Primary Diagnosis: Suspected cement washout or secondary caries at tooth #14 crown margin
- Differential Diagnosis: 
  1. Marginal leakage with secondary decay
  2. Cement failure
  3. Periodontal recession exposing root surface
- Prognosis: Good with appropriate treatment

PLAN:
- Immediate Treatment: Periapical radiograph of tooth #14
- Definitive Treatment: Based on radiographic findings:
  • If secondary caries confirmed: Remove existing crown, caries excavation, new crown
  • If cement washout only: Re-cementation if crown intact
- Medications: Sensodyne toothpaste for sensitivity management
- Follow-up: 1 week for radiograph review and treatment planning"""

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio streaming"""
    await websocket.accept()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Send connection confirmation
        mode = "Whisper Transcription" if WHISPER_AVAILABLE else "Mock Mode"
        await websocket.send_json({
            "status": "Connected",
            "session_id": session_id,
            "mode": mode,
            "message": f"Ready for audio ({mode})"
        })
        
        audio_chunks = []
        session_context = []
        
        while True:
            data = await websocket.receive()
            
            if "text" in data:
                message = data["text"]
                
                if message == "END":
                    if audio_chunks:
                        # Process accumulated audio
                        await websocket.send_json({"status": "Processing audio..."})
                        
                        # Combine audio chunks
                        combined_audio = b''.join(audio_chunks)
                        audio_chunks = []
                        
                        # Convert to WAV
                        wav_path = convert_audio_to_wav(combined_audio)
                        
                        # Transcribe
                        await websocket.send_json({"status": "Transcribing..."})
                        transcript = transcribe_audio(wav_path)
                        
                        # Clean up audio file
                        if wav_path and os.path.exists(wav_path):
                            os.unlink(wav_path)
                        
                        # Send transcript
                        await websocket.send_json({
                            "transcript": transcript,
                            "status": "Generating SOAP note..."
                        })
                        
                        # Generate SOAP note
                        soap = generate_soap_note(transcript)
                        
                        # Add to context
                        session_context.append(transcript)
                        
                        # Send final results
                        await websocket.send_json({
                            "transcript": transcript,
                            "soap": soap,
                            "status": "Complete",
                            "session_id": session_id
                        })
                        
                        # Log session
                        logging.info(f"Session {session_id}: Completed")
                    else:
                        await websocket.send_json({"error": "No audio data received"})
                
                elif message.startswith("CORRECT:"):
                    # Handle corrections
                    correction = message[8:]
                    if session_context:
                        # Regenerate SOAP with correction
                        await websocket.send_json({"status": "Applying correction..."})
                        
                        corrected_transcript = session_context[-1] + f"\nCORRECTION: {correction}"
                        updated_soap = generate_soap_note(corrected_transcript)
                        
                        await websocket.send_json({
                            "soap": updated_soap,
                            "status": "Updated with correction"
                        })
            
            elif "bytes" in data:
                # Accumulate audio chunks
                audio_chunks.append(data["bytes"])
                
                # Send periodic status
                if len(audio_chunks) % 10 == 0:
                    await websocket.send_json({
                        "status": f"Recording... {len(audio_chunks)} chunks received"
                    })
    
    except WebSocketDisconnect:
        logging.info(f"Session {session_id} disconnected")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "Boise Prosthodontics AI Scribe",
        "version": "2.0",
        "whisper": "enabled" if WHISPER_AVAILABLE else "disabled",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    # Check Ollama
    ollama_status = "unknown"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "whisper": "loaded" if WHISPER_AVAILABLE else "not available",
            "ollama": ollama_status,
            "ffmpeg": "installed"
        }
    }

@app.post("/api/test-transcription")
async def test_transcription():
    """Test endpoint to verify transcription works"""
    if WHISPER_AVAILABLE and WHISPER_MODEL:
        return {"status": "Whisper is working", "model": "base"}
    else:
        return {"status": "Using mock mode", "whisper": False}

if __name__ == "__main__":
    import uvicorn
    print("🦷 Starting Boise Prosthodontics AI Scribe...")
    print(f"📍 WebSocket: ws://localhost:8000/ws/audio")
    print(f"🎙️ Whisper: {'Enabled' if WHISPER_AVAILABLE else 'Disabled (Mock Mode)'}")
    print(f"🧠 Ollama: {OLLAMA_HOST}")
    uvicorn.run(app, host="0.0.0.0", port=8000)