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

def convert_template_name_to_id(template_name):
    """Convert old template names to new IDs"""
    if not template_name:
        return "new_patient_consultation"
    
    # Mapping for old names
    template_mapping = {
        "work_up": "new_patient_consultation",
        "Work Up": "new_patient_consultation", 
        "default": "new_patient_consultation"
    }
    
    return template_mapping.get(template_name, template_name)

@app.post("/api/regenerate_soap")
async def regenerate_soap(request: dict):
    """Regenerate SOAP note with new template"""
    try:
        session_id = request.get("session_id")
        raw_template = request.get("template")
        transcript = request.get("transcript", "")
        doctor_name = request.get("doctor", "Dr. Provider")
        
        # Convert old template names to new ones
        new_template = convert_template_name_to_id(raw_template)
        
        logging.info(f"🔄 Regenerating SOAP for session {session_id} with template {raw_template} -> {new_template}")
        
        # Generate new SOAP note
        soap_note = generate_soap_note(transcript, new_template, doctor_name)
        
        # Update session if it exists
        session = session_manager.get_session(session_id)
        if session:
            session_manager.update_session(session_id, 
                                         soap_note=soap_note, 
                                         template=new_template)
        
        return {
            "success": True,
            "soap_note": soap_note,
            "message": "SOAP note regenerated successfully"
        }
        
    except Exception as e:
        logging.error(f"Error regenerating SOAP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions():
    """Get all sessions"""
    # Return mock sessions for testing
    return [
        {
            "session_id": "20251013_212247",
            "doctor_name": "Michael Gurney",
            "timestamp": "2025-10-13T21:22:47",
            "patient_name": None,
            "template_used": "new_patient_consultation",  # Fixed: no more "Work Up"
            "has_soap": True,
            "has_transcript": True
        }
    ]

@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    """Get session details"""
    # Return mock session data for testing
    if session_id == "20251013_212247":
        return {
            "session_id": session_id,
            "doctor_name": "Michael Gurney", 
            "timestamp": "2025-10-13T21:22:47",
            "patient_name": None,
            "template_used": "new_patient_consultation",  # Fixed: no more "Work Up"
            "transcript": """Doctor (Michael Gurney): Hi, nice to meet you. I am Dr. Gurney. I appreciate you coming in today, excited to talk
Doctor (Michael Gurney): with you about what we can do and what your needs might be. From my understanding, you have a broken
Doctor (Michael Gurney): front tooth and your seeking, some advice and counsel on what needs to be done to help you in your
Doctor (Michael Gurney): situation. As I look at a broken front tooth, I always have to think of what is your primary
Doctor (Michael Gurney): concern with it. Do you want to just have a replacement that looks good or do you want to have
Doctor (Michael Gurney): a functional stable tooth that you can eat just like normal like anything else? When you're missing
Doctor (Michael Gurney): a front tooth, there's a couple options that are available to replace it. One, the most simplest
Doctor (Michael Gurney): option is to replace it with a removable partial denture. Some people call it a flipper. That's
Doctor (Michael Gurney): little wires that hold it in place. It's not necessarily that functional, but it can look good.
Doctor (Michael Gurney): Another solution might be a partial denture, which actually has a metal framework and a tooth
Doctor (Michael Gurney): attached to it and it slides in around the teeth. It too comes in and out just like a flipper might.
Doctor (Michael Gurney): But it is a possible solution to replacing a missing tooth. More of the functional and stable""",
            "soap_note": """PROSTHODONTIC CONSULTATION NOTE
Provider: Michael Gurney
Date: October 13, 2025

SUBJECTIVE:
Patient presented for consultation regarding a broken front tooth. Dr. Gurney asked about the patient's primary concern and treatment goals. Patient seeking advice and counsel on treatment options for the broken front tooth situation.

OBJECTIVE:
Clinical consultation focused on treatment options for broken front tooth replacement. Multiple treatment modalities discussed including:
- Removable partial denture (flipper) - simplest option with little wires for retention, primarily aesthetic function
- Partial denture with metal framework - more stable option that slides around existing teeth
- Discussion of functional vs. aesthetic priorities for tooth replacement

ASSESSMENT:
Patient requires front tooth replacement with consideration of both functional and aesthetic needs.

PLAN:
Treatment options presented and discussed with patient. Further evaluation needed to determine optimal treatment approach based on patient preferences and clinical factors."""
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MINIMAL Boise Prosthodontics AI Scribe...")
    print("📋 Available templates:", [t['name'] for t in template_manager.get_template_list()])
    uvicorn.run(app, host="0.0.0.0", port=3051, log_level="info")