from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime
import json
import requests
from pathlib import Path

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

# Ollama configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama:11434')

def generate_mock_transcript():
    """Generate a mock transcript for testing"""
    return """Doctor: Good morning, what brings you in today?
Patient: I've been having pain in my upper left molar, tooth number 14.
Doctor: How long has this been bothering you?
Patient: About a week now, and it's getting worse.
Doctor: Let me examine that area. I can see some inflammation around the crown.
Patient: Is it serious?
Doctor: The crown appears to be failing. We'll need to replace it.
Patient: What's the timeline for that?
Doctor: We can do a temporary crown today and schedule the permanent one in two weeks."""

def generate_soap_note(transcript):
    """Generate SOAP note using Ollama or fallback"""
    prompt = f"""Convert this dental consultation into a SOAP note:

{transcript}

Format as:
SUBJECTIVE:
OBJECTIVE:
ASSESSMENT:
PLAN:"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('response', 'Error generating SOAP')
    except Exception as e:
        logging.error(f"Ollama error: {e}")
    
    # Fallback SOAP note
    return """SUBJECTIVE:
- Chief Complaint: Pain in upper left molar (tooth #14)
- Duration: 1 week, progressively worsening
- Patient reports discomfort with existing crown

OBJECTIVE:
- Clinical examination reveals inflammation around tooth #14
- Existing crown shows signs of failure
- Periapical tissues inflamed

ASSESSMENT:
- Failed crown on tooth #14 with associated inflammation
- Requires crown replacement

PLAN:
- Temporary crown placement today
- Schedule permanent crown in 2 weeks
- Prescribe anti-inflammatory as needed
- Follow-up after permanent crown placement"""

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "status": "Connected",
            "session_id": session_id,
            "message": "Ready for audio (using mock mode for testing)"
        })
        
        audio_chunks = []
        
        while True:
            data = await websocket.receive()
            
            if "text" in data and data["text"] == "END":
                # Process with mock data for now
                await websocket.send_json({"status": "Processing..."})
                
                # Generate mock transcript
                transcript = generate_mock_transcript()
                await websocket.send_json({
                    "transcript": transcript,
                    "status": "Generating SOAP..."
                })
                
                # Generate SOAP note
                soap = generate_soap_note(transcript)
                await websocket.send_json({
                    "transcript": transcript,
                    "soap": soap,
                    "status": "Complete"
                })
                
            elif "bytes" in data:
                audio_chunks.append(data["bytes"])
                if len(audio_chunks) % 10 == 0:
                    await websocket.send_json({
                        "status": f"Recording... {len(audio_chunks)} chunks"
                    })
    
    except WebSocketDisconnect:
        logging.info(f"Session {session_id} disconnected")
    except Exception as e:
        logging.error(f"Error: {e}")
        await websocket.send_json({"error": str(e)})

@app.get("/")
async def root():
    return {
        "service": "Boise Prosthodontics AI Scribe",
        "mode": "Mock Mode (Whisper disabled for testing)",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    # Check Ollama
    ollama_status = "unknown"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy",
        "mode": "mock",
        "ollama": ollama_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🦷 Starting Boise Prosthodontics AI Scribe (Mock Mode)...")
    print(f"📍 WebSocket: ws://localhost:3051/ws/audio")
    uvicorn.run(app, host="0.0.0.0", port=3051)