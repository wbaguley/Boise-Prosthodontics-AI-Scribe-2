from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
import logging
from datetime import datetime
from templates import TemplateManager

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize template manager
template_manager = TemplateManager()

# LLM Configuration
LLM_CONFIGS = {
    "llama": {
        "name": "Llama 3.2 (Local)",
        "host": "http://localhost:11434",
        "model": "llama3.2"
    }
}

current_llm_config = LLM_CONFIGS["llama"]

def get_current_llm_config():
    return current_llm_config

def generate_soap_note(transcript, template_name="new_patient_consultation", doctor_name=""):
    """Generate SOAP note using Ollama with template"""
    
    logging.info(f"🔍 SOAP Generation Debug:")
    logging.info(f"   Requested template: {template_name}")
    logging.info(f"   Doctor name: {doctor_name}")
    
    template = template_manager.get_template(template_name)
    ai_instructions = ""
    template_sections = {}
    
    if template:
        logging.info(f"   ✅ Template found: {template.get('name', 'Unknown')}")
        ai_instructions = template.get("ai_instructions", "")
        template_sections = template.get("sections", {})
    else:
        logging.warning(f"   ❌ Template '{template_name}' not found!")
        # Use first available template as fallback
        available_templates = template_manager.get_template_list()
        if available_templates:
            fallback_template_id = available_templates[0]['id']
            logging.warning(f"   🔄 Falling back to: {fallback_template_id}")
            template = template_manager.get_template(fallback_template_id)
            if template:
                ai_instructions = template.get("ai_instructions", "")
                template_sections = template.get("sections", {})

    # Enhanced prompt to prevent plagiarism responses
    prompt = f"""🔴 MANDATORY CLINICAL DOCUMENTATION 🔴

SYSTEM IDENTITY: You are Dr. {doctor_name} creating an official clinical SOAP note.

ABSOLUTE PROHIBITIONS - NEVER SAY:
- "plagiarism" or "cannot write" 
- "not based on actual" or "help you with writing"
- "see transcript" or "as discussed"
- "based on consultation" or "documented in transcript"

📋 TEMPLATE STRUCTURE:
{json.dumps(template_sections, indent=2) if template_sections else "Standard SOAP format"}

📜 CLINICAL INSTRUCTIONS:
{ai_instructions if ai_instructions else "Write a comprehensive SOAP note."}

🗣️ PATIENT ENCOUNTER TRANSCRIPT:
{transcript}

⚡ REQUIREMENTS ⚡
1. Write as Dr. {doctor_name} documenting your patient encounter
2. Extract ALL specific details from the transcript
3. Include exact patient statements and clinical observations  
4. Follow the template structure exactly
5. Apply all clinical instructions precisely
6. Write in first person as the treating doctor
7. Create a complete, professional medical record

WRITE THE SOAP NOTE IMMEDIATELY:"""

    try:
        llm_config = get_current_llm_config()
        response = requests.post(
            f"{llm_config['host']}/api/generate",
            json={
                "model": llm_config["model"], 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "repeat_penalty": 1.3
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            soap_content = response.json().get('response', '')
            
            # Check for forbidden phrases
            forbidden_phrases = ["plagiarism", "cannot write", "not based on actual", "help you with writing"]
            soap_lower = soap_content.lower()
            violations = [phrase for phrase in forbidden_phrases if phrase in soap_lower]
            
            if violations:
                logging.error(f"❌ SOAP note contains forbidden phrases: {violations}")
                return generate_fallback_soap(transcript, template_sections, doctor_name)
            
            return soap_content
            
    except Exception as e:
        logging.error(f"Ollama error: {e}")
    
    return generate_fallback_soap(transcript, template_sections, doctor_name)

def generate_fallback_soap(transcript, template_sections, doctor_name):
    """Generate fallback SOAP note"""
    
    # Extract patient and doctor statements
    lines = transcript.split('\n')
    patient_statements = []
    doctor_statements = []
    
    for line in lines:
        line = line.strip()
        if line.startswith(('Patient:', 'Pt:', 'P:')):
            patient_statements.append(line.replace('Patient:', '').replace('Pt:', '').replace('P:', '').strip())
        elif line.startswith(('Doctor:', 'Dr:', 'D:')):
            doctor_statements.append(line.replace('Doctor:', '').replace('Dr:', '').replace('D:', '').strip())
    
    current_time = datetime.now().strftime("%B %d, %Y")
    soap_note = f"PROSTHODONTIC CONSULTATION NOTE\nProvider: {doctor_name}\nDate: {current_time}\n\n"
    
    # SUBJECTIVE
    soap_note += "SUBJECTIVE:\n"
    if patient_statements:
        soap_note += f"Patient presented stating: \"{patient_statements[0]}\"\n"
        for stmt in patient_statements[1:3]:
            soap_note += f"Patient also mentioned: \"{stmt}\"\n"
    else:
        soap_note += "Patient consultation for prosthodontic evaluation.\n"
    
    # OBJECTIVE  
    soap_note += "\nOBJECTIVE:\n"
    if doctor_statements:
        soap_note += "Clinical examination and consultation findings:\n"
        for stmt in doctor_statements[:3]:
            soap_note += f"- {stmt}\n"
    else:
        soap_note += "Clinical examination completed.\n"
    
    # ASSESSMENT
    soap_note += "\nASSESSMENT:\n"
    soap_note += "Prosthodontic evaluation completed.\n"
    
    # PLAN  
    soap_note += "\nPLAN:\n"
    soap_note += "Treatment recommendations discussed with patient.\n"
    soap_note += "Follow-up as appropriate.\n"
    
    return soap_note

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id):
        self.sessions[session_id] = {
            'audio_chunks': [],
            'transcript': "",
            'soap_note': "",
            'doctor_name': "",
            'template': "new_patient_consultation"
        }

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def update_session(self, session_id, **kwargs):
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)

session_manager = SessionManager()

@app.websocket("/ws/record")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_manager.create_session(session_id)
    
    doctor_name = "Dr. Provider"
    template_name = "new_patient_consultation"
    
    try:
        await websocket.send_json({
            "status": "Connected",
            "session_id": session_id,
            "message": "Ready (Mock mode)"
        })
        
        while True:
            data = await websocket.receive()
            
            if "text" in data:
                try:
                    message = json.loads(data["text"])
                    if message.get("type") == "session_info":
                        doctor_name = message.get("doctor", "Dr. Provider")
                        template_name = message.get("template", "new_patient_consultation")
                        logging.info(f"Session info - Doctor: {doctor_name}, Template: {template_name}")
                        
                    elif message.get("type") == "stop_recording":
                        # Mock transcript for testing
                        transcript = """Doctor (Wyatt Test): I have a patient here that is complaining of tooth pain. We're going to go ahead and take a look and get a x-ray
Doctor (Wyatt Test): scheduled with them. They are 34 years old. They haven't had any prior surgery. They're not allergic
Doctor (Wyatt Test): to any medications. They have been having this pain for the past two weeks, and they are looking
Doctor (Wyatt Test): for a extraction, along with a possible implant installation. We need to do a workup and measurements
Doctor (Wyatt Test): for that, and get some orders in to get that done."""
                        
                        session_manager.update_session(session_id, 
                                                     transcript=transcript, 
                                                     doctor_name=doctor_name,
                                                     template=template_name)
                        
                        await websocket.send_json({
                            "status": "Transcription Complete",
                            "transcript": transcript,
                            "message": "Generating SOAP note..."
                        })
                        
                        # Generate SOAP note
                        soap = generate_soap_note(transcript, template_name, doctor_name)
                        session_manager.update_session(session_id, soap_note=soap)
                        
                        await websocket.send_json({
                            "status": "SOAP Generated",
                            "soap_note": soap,
                            "session_id": session_id,
                            "message": "Session completed successfully"
                        })
                        
                except json.JSONDecodeError as e:
                    logging.error(f"JSON decode error: {e}")
            
            elif "bytes" in data:
                # Mock audio processing
                await websocket.send_json({
                    "status": "Recording", 
                    "message": "Audio received (mock mode)"
                })
                
    except WebSocketDisconnect:
        logging.info(f"Client disconnected from session {session_id}")

@app.get("/api/templates")
async def get_templates():
    return template_manager.get_templates()

@app.get("/api/templates/list")
async def get_template_list():
    return template_manager.get_template_list()

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MINIMAL Boise Prosthodontics AI Scribe...")
    print("📋 Available templates:", [t['name'] for t in template_manager.get_template_list()])
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")