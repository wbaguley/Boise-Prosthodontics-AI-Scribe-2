from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file in the parent directory
load_dotenv(dotenv_path="../.env")
from datetime import datetime
import json
import requests
from pathlib import Path
import tempfile
import subprocess
import warnings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from cryptography.fernet import Fernet
import base64
import hashlib

# Suppress warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
WHISPER_MODEL_SIZE = os.getenv('WHISPER_MODEL', 'tiny')
HF_TOKEN = os.getenv('HF_TOKEN', '')

# Import database functions
from database import (
    save_session, get_all_sessions, get_session_by_id, get_sessions_by_provider,
    create_provider, get_all_providers, get_provider_by_id, get_provider_by_name,
    update_provider, delete_provider, update_provider_voice_profile,
    update_session_patient_info, update_session_email_content, mark_email_sent, get_session_email_status,
    update_session_soap, update_session_template
)
from templates import TemplateManager
from voice_profile_manager import VoiceProfileManager

# Initialize managers
template_manager = TemplateManager()
voice_manager = VoiceProfileManager()

# Try to load models
WHISPER_AVAILABLE = False
WHISPER_MODEL = None
DIARIZATION_AVAILABLE = False
DIARIZATION_PIPELINE = None

# Load Whisper
try:
    print(f"Loading Whisper model...")
    import whisper
    import torch
    import torchaudio
    torch.set_default_dtype(torch.float32)
    WHISPER_MODEL = whisper.load_model(WHISPER_MODEL_SIZE)
    WHISPER_AVAILABLE = True
    print(f"[OK] Whisper {WHISPER_MODEL_SIZE} model loaded successfully!")
except Exception as e:
    print(f"[WARNING] Whisper not available: {e}")
    WHISPER_AVAILABLE = False
    whisper = None
    torch = None

# Load Pyannote diarization
try:
    if HF_TOKEN and torch is not None:
        print(f"Loading speaker diarization model...")
        from pyannote.audio import Pipeline
        DIARIZATION_PIPELINE = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
        if torch.cuda.is_available():
            DIARIZATION_PIPELINE.to(torch.device("cuda"))
        DIARIZATION_AVAILABLE = True
        print(f"[OK] Speaker diarization loaded successfully!")
    else:
        print("[WARNING] No HF_TOKEN provided, using voice profile matching")
except Exception as e:
    print(f"[WARNING] Speaker diarization not available: {e}")

# Pydantic models
class SessionInfo(BaseModel):
    doctor: str
    template: Optional[str] = "default"

class ProviderCreate(BaseModel):
    name: str
    specialty: Optional[str] = None
    credentials: Optional[str] = None
    email: Optional[str] = None

class ProviderUpdate(BaseModel):
    specialty: Optional[str] = None
    credentials: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class CorrectionRequest(BaseModel):
    original_soap: str
    correction: str
    transcript: str

class ChatMessage(BaseModel):
    role: str
    content: str

class SoapEditChatRequest(BaseModel):
    original_soap: str
    transcript: str
    user_message: str
    chat_history: List[ChatMessage] = []

class PatientLookupRequest(BaseModel):
    patient_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class PatientInfo(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[Dict] = None

class PostVisitEmailRequest(BaseModel):
    session_id: str
    patient_info: PatientInfo
    email_content: str
    email_subject: str

class EmailGenerationRequest(BaseModel):
    soap_note: str
    transcript: Optional[str] = None
    patient_name: str
    provider_name: str
    appointment_date: Optional[str] = None

class KnowledgeArticle(BaseModel):
    title: str
    content: str
    category: str

class TrainingChatRequest(BaseModel):
    message: str

# Encryption utilities for HIPAA compliance
class EncryptionManager:
    def __init__(self):
        # Generate or load encryption key
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)
    
    def _get_or_create_key(self):
        key_file = Path("encryption_key.key")
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted = self.cipher_suite.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted.decode()

# Initialize encryption manager
encryption_manager = EncryptionManager()

class SessionManager:
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, session_id: str, doctor: str = None, provider_id: int = None):
        self.sessions[session_id] = {
            'doctor': doctor,
            'provider_id': provider_id,
            'transcript': '',
            'soap_note': '',
            'audio_chunks': [],
            'template': 'default',
            'doctor_voice_registered': False
        }
    
    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

session_manager = SessionManager()

def convert_audio_to_wav(audio_data):
    """Convert webm audio to wav using ffmpeg"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as webm_file:
            webm_file.write(audio_data)
            webm_path = webm_file.name
        
        wav_path = tempfile.mktemp(suffix='.wav')
        
        cmd = [
            'ffmpeg', '-y', '-i', webm_path,
            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            wav_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(webm_path)
        
        if result.returncode == 0:
            return wav_path
        else:
            logging.error(f"FFmpeg error: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Audio conversion error: {e}")
        return None

def diarize_audio(audio_path):
    """Perform speaker diarization on audio file"""
    if not DIARIZATION_AVAILABLE or not DIARIZATION_PIPELINE:
        return None
    
    try:
        diarization = DIARIZATION_PIPELINE(audio_path)
        
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        return segments
    except Exception as e:
        logging.error(f"Diarization error: {e}")
        return None

def transcribe_audio_with_diarization(audio_path, doctor_name="", use_voice_profile=False):
    """Transcribe audio with speaker detection - single speaker mode"""
    
    if not WHISPER_AVAILABLE or not WHISPER_MODEL:
        return generate_mock_transcript()
    
    try:
        # Get transcription with timestamps
        result = WHISPER_MODEL.transcribe(
            audio_path,
            language="en",
            word_timestamps=True,
            initial_prompt="This is a dental consultation about crowns, implants, and prosthodontics."
        )
        
        # Get speaker diarization if available
        speaker_segments = None
        
        if DIARIZATION_AVAILABLE:
            speaker_segments = diarize_audio(audio_path)
        
        # Process segments
        formatted_lines = []
        
        if speaker_segments:
            # Map transcription to speakers using diarization
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if not text:
                    continue
                
                segment_start = segment.get("start", 0)
                segment_end = segment.get("end", 0)
                segment_mid = (segment_start + segment_end) / 2
                
                # Find which speaker this belongs to
                speaker = "Unknown"
                for speaker_seg in speaker_segments:
                    if speaker_seg['start'] <= segment_mid <= speaker_seg['end']:
                        # Map speaker labels to Doctor/Patient
                        if speaker_seg['speaker'] == 'SPEAKER_00':
                            speaker = f"Doctor ({doctor_name})" if doctor_name else "Doctor"
                        else:
                            speaker = "Patient"
                        break
                
                formatted_lines.append(f"{speaker}: {text}")
        else:
            # Single speaker mode - label everything as Doctor
            # This is more accurate when only the doctor is speaking
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if not text:
                    continue
                
                speaker_label = f"Doctor ({doctor_name})" if doctor_name else "Doctor"
                formatted_lines.append(f"{speaker_label}: {text}")
        
        return "\n".join(formatted_lines)
        
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return f"Transcription error: {str(e)}"

def generate_mock_transcript():
    """Generate mock transcript for testing"""
    return """Doctor: Good morning, what brings you in today?
Patient: I've been having pain in my upper left molar, tooth number 14.
Doctor: How long has this been bothering you?
Patient: About a week now, and it's getting worse.
Doctor: Let me examine that area. I can see some inflammation around the crown.
Patient: Is it serious?
Doctor: The crown appears to be failing. We'll need to replace it."""

def generate_soap_note(transcript, template_name="default", doctor_name=""):
    """Generate SOAP note using Ollama with template"""
    
    template = template_manager.get_template(template_name)
    template_prompt = ""
    ai_instructions = ""
    
    if template:
        # Extract AI instructions if available
        ai_instructions = template.get("ai_instructions", "")
        template_sections = template.get("sections", {})
        
        if template_sections:
            template_prompt = f"Use this SOAP template structure:\n{json.dumps(template_sections, indent=2)}\n\n"
        
        if ai_instructions:
            template_prompt += f"Special Instructions: {ai_instructions}\n\n"
    
    prompt = f"""You are Dr. {doctor_name}, a prosthodontist documenting a patient consultation. Based on the following consultation notes, create a professional SOAP note.

{template_prompt}

Consultation Details:
{transcript}

Instructions:
- Create a structured SOAP note following proper format
- SUBJECTIVE: Document patient complaints, concerns, and relevant history
- OBJECTIVE: Record clinical examination findings and observations  
- ASSESSMENT: Provide professional diagnosis or clinical assessment
- PLAN: Outline treatment recommendations and next steps
- Use appropriate dental terminology and tooth numbering system (1-32)
- Write in professional medical documentation style
- Do not reference "transcript" or "recording" in the SOAP note content
- Present information as direct clinical observations and patient reports

{ai_instructions if ai_instructions else ""}"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get('response', generate_fallback_soap(transcript))
    except Exception as e:
        logging.error(f"Ollama error: {e}")
    
    return generate_fallback_soap(transcript)

def generate_fallback_soap(transcript):
    """Generate fallback SOAP note"""
    return f"""SUBJECTIVE:
- Chief Complaint: Dental consultation
- History: See transcript

OBJECTIVE:
- Clinical examination performed
- Findings documented in transcript

ASSESSMENT:
- Based on consultation findings

PLAN:
- As discussed in consultation
- Follow-up as needed

---
Full Transcript:
{transcript}"""

def generate_post_visit_email(soap_note: str, patient_name: str, provider_name: str, appointment_date: str = None, transcript: str = None):
    """Generate a patient-friendly post-visit summary email using AI"""
    try:
        # Create prompt for email generation
        current_date = datetime.now().strftime("%B %d, %Y") if not appointment_date else appointment_date
        
        prompt = f"""Create a professional, warm, and patient-friendly post-visit summary email based on the following information from a dental appointment.

SOAP NOTE:
{soap_note}

CONVERSATION TRANSCRIPT:
{transcript if transcript else "No transcript available"}

PATIENT INFORMATION:
- Patient Name: {patient_name}
- Provider: {provider_name}  
- Visit Date: {current_date}

EMAIL REQUIREMENTS:
1. Start with "Dear {patient_name},"
2. Reference the specific visit date
3. Summarize the key findings from the SOAP note in simple, patient-friendly language
4. Include what was discussed during the visit (use transcript details)
5. Explain any treatments or procedures that were performed
6. List clear next steps and recommendations
7. Include follow-up instructions or appointment scheduling needs
8. Add contact information for questions
9. Close professionally with the doctor's name
10. Keep medical terminology simple and explain complex terms

IMPORTANT: 
- Use actual details from the SOAP note and transcript provided
- Convert medical terms to patient-friendly language
- Be specific about findings and recommendations
- Make it personal and caring, not generic

Generate the email with Subject: and Body: clearly marked:"""

        # Call Ollama API
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            email_content = result.get('response', '').strip()
            
            # Parse subject and body
            lines = email_content.split('\n')
            subject_line = ""
            body_content = ""
            
            for i, line in enumerate(lines):
                if line.lower().startswith('subject:'):
                    subject_line = line.replace('Subject:', '').replace('subject:', '').strip()
                    body_content = '\n'.join(lines[i+1:]).strip()
                    break
            
            if not subject_line:
                subject_line = f"Follow-up from your visit on {current_date}"
                body_content = email_content
            
            return {
                "subject": subject_line,
                "body": body_content
            }
            
    except Exception as e:
        logging.error(f"Error generating post-visit email: {e}")
        # Fallback email
        return {
            "subject": f"Follow-up from your visit with {provider_name}",
            "body": f"""Dear {patient_name},

Thank you for visiting our office today. We hope you had a positive experience during your appointment.

Based on your visit, we have documented your treatment plan and any recommendations discussed. Please review the information we provided and don't hesitate to contact our office if you have any questions.

Next Steps:
- Follow any post-treatment instructions provided
- Schedule your next appointment as recommended
- Contact us with any concerns or questions

We appreciate your trust in our practice and look forward to seeing you again soon.

Best regards,
{provider_name}

---
If you have any questions about this summary or your treatment, please contact our office."""
        }

async def lookup_patient_dentrix(lookup_data: PatientLookupRequest):
    """Lookup patient information from Dentrix API"""
    try:
        # Note: This is a template for Dentrix API integration
        # You'll need to configure the actual Dentrix API endpoint and authentication
        
        dentrix_api_url = os.getenv('DENTRIX_API_URL', 'https://api.dentrix.com/v1')
        dentrix_api_key = os.getenv('DENTRIX_API_KEY', '')
        
        if not dentrix_api_key:
            raise HTTPException(status_code=500, detail="Dentrix API not configured")
        
        # Build search parameters
        params = {}
        if lookup_data.patient_id:
            params['patientId'] = lookup_data.patient_id
        if lookup_data.first_name:
            params['firstName'] = lookup_data.first_name
        if lookup_data.last_name:
            params['lastName'] = lookup_data.last_name
        if lookup_data.email:
            params['email'] = lookup_data.email
        if lookup_data.phone:
            params['phone'] = lookup_data.phone
        
        # Make API call to Dentrix
        headers = {
            'Authorization': f'Bearer {dentrix_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{dentrix_api_url}/patients/search",
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            patient_data = response.json()
            
            # Process and encrypt sensitive data
            if patient_data.get('patients'):
                patients = []
                for patient in patient_data['patients']:
                    # Encrypt sensitive information
                    encrypted_patient = {
                        "patient_id": patient.get('id', ''),
                        "first_name": patient.get('firstName', ''),
                        "last_name": patient.get('lastName', ''),
                        "email": encryption_manager.encrypt_data(patient.get('email', '')),
                        "phone": encryption_manager.encrypt_data(patient.get('phone', '')) if patient.get('phone') else None,
                        "date_of_birth": patient.get('dateOfBirth', ''),
                        "address": {
                            "street": encryption_manager.encrypt_data(patient.get('address', {}).get('street', '')),
                            "city": patient.get('address', {}).get('city', ''),
                            "state": patient.get('address', {}).get('state', ''),
                            "zip": encryption_manager.encrypt_data(patient.get('address', {}).get('zip', ''))
                        } if patient.get('address') else None
                    }
                    patients.append(encrypted_patient)
                
                return {"patients": patients}
            else:
                return {"patients": []}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to lookup patient in Dentrix")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Dentrix API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Dentrix API")
    except Exception as e:
        logging.error(f"Patient lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Patient lookup failed: {str(e)}")

async def send_patient_email(email_data: PostVisitEmailRequest):
    """Send post-visit summary email to patient"""
    try:
        # SMTP configuration (should be in environment variables)
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not all([smtp_username, smtp_password]):
            raise HTTPException(status_code=500, detail="Email configuration not found")
        
        # Decrypt patient email
        patient_email = encryption_manager.decrypt_data(email_data.patient_info.email)
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email_data.email_subject
        msg['From'] = smtp_username
        msg['To'] = patient_email
        
        # Convert HTML to plain text for email clients that don't support HTML
        html_content = email_data.email_content
        
        # Create both HTML and plain text versions
        html_part = MIMEText(html_content, 'html')
        
        # Simple HTML to text conversion
        text_content = re.sub(r'<[^>]+>', '', html_content)
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
        text_part = MIMEText(text_content, 'plain')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        # Log the email send (without sensitive data)
        logging.info(f"Post-visit email sent for session {email_data.session_id}")
        
        return {"status": "success", "message": "Email sent successfully"}
        
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# ============================================
# Provider Management API Endpoints
# ============================================

@app.post("/api/providers")
async def create_provider_endpoint(provider: ProviderCreate):
    """Create a new provider"""
    result = create_provider(
        name=provider.name,
        specialty=provider.specialty,
        credentials=provider.credentials,
        email=provider.email
    )
    
    if result:
        return result
    else:
        raise HTTPException(status_code=400, detail="Provider already exists or creation failed")

@app.get("/api/providers")
async def get_providers(active_only: bool = True):
    """Get all providers"""
    return get_all_providers(active_only=active_only)

@app.get("/api/providers/{provider_id}")
async def get_provider(provider_id: int):
    """Get specific provider by ID"""
    provider = get_provider_by_id(provider_id)
    if provider:
        return provider
    raise HTTPException(status_code=404, detail="Provider not found")

@app.put("/api/providers/{provider_id}")
async def update_provider_endpoint(provider_id: int, provider: ProviderUpdate):
    """Update provider information"""
    update_data = {k: v for k, v in provider.dict().items() if v is not None}
    
    result = update_provider(provider_id, **update_data)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Provider not found")

@app.delete("/api/providers/{provider_id}")
async def delete_provider_endpoint(provider_id: int):
    """Soft delete a provider"""
    success = delete_provider(provider_id)
    if success:
        return {"status": "Provider deleted successfully"}
    raise HTTPException(status_code=404, detail="Provider not found")

# ============================================
# Voice Profile API Endpoints
# ============================================

@app.post("/api/voice-profile")
async def save_voice_profile(
    doctor_name: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Save voice profile for speaker identification"""
    try:
        # Get or create provider
        provider = get_provider_by_name(doctor_name)
        if not provider:
            provider = create_provider(name=doctor_name)
            if not provider:
                raise HTTPException(status_code=400, detail="Could not create provider")
        
        # Save audio samples to temp files
        temp_files = []
        for i, file in enumerate(files):
            if file.filename:
                # Save to temp location
                temp_path = Path(tempfile.gettempdir()) / f"voice_sample_{i}_{datetime.now().timestamp()}.wav"
                content = await file.read()
                
                # Convert to WAV if needed
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                    temp_file.write(content)
                    temp_webm = temp_file.name
                
                # Convert using ffmpeg
                cmd = [
                    'ffmpeg', '-y', '-i', temp_webm,
                    '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                    str(temp_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True)
                os.unlink(temp_webm)
                
                if result.returncode == 0:
                    temp_files.append(str(temp_path))
        
        if not temp_files:
            raise HTTPException(status_code=400, detail="No valid audio files")
        
        # Create voice profile
        profile_info = voice_manager.create_profile(doctor_name, temp_files)
        
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        if profile_info:
            # Update provider record
            update_provider_voice_profile(
                provider['id'],
                profile_info['profile_path']
            )
            
            logging.info(f"Voice profile created for {doctor_name}")
            return {
                "status": "Voice profile saved successfully",
                "provider": doctor_name,
                "samples": profile_info['num_samples']
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create voice profile")
        
    except Exception as e:
        logging.error(f"Error saving voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save voice profile: {str(e)}")

@app.get("/api/voice-profiles")
async def get_voice_profiles():
    """Get list of available voice profiles"""
    profiles = voice_manager.list_profiles()
    return {"profiles": profiles}

@app.get("/api/voice-profile/{provider_name}")
async def get_voice_profile_info(provider_name: str):
    """Get information about a specific voice profile"""
    info = voice_manager.get_profile_info(provider_name)
    if info:
        return info
    raise HTTPException(status_code=404, detail="Voice profile not found")

@app.delete("/api/voice-profile/{provider_name}")
async def delete_voice_profile(provider_name: str):
    """Delete a voice profile"""
    try:
        success = voice_manager.delete_profile(provider_name)
        
        if success:
            # Update provider record
            provider = get_provider_by_name(provider_name)
            if provider:
                update_provider(
                    provider['id'],
                    has_voice_profile=False,
                    voice_profile_path=None
                )
            
            logging.info(f"Deleted voice profile for {provider_name}")
            return {"status": "Voice profile deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Voice profile not found")
            
    except Exception as e:
        logging.error(f"Error deleting voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete voice profile: {str(e)}")

# ============================================
# WebSocket Audio Processing
# ============================================

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_manager.create_session(session_id)
    
    doctor_name = None
    provider_id = None
    template_name = "default"
    use_voice_profile = False
    
    try:
        mode = "Whisper" if WHISPER_AVAILABLE else "Mock"
        diarization_status = "with diarization" if DIARIZATION_AVAILABLE else "single speaker mode"
        
        await websocket.send_json({
            "status": "Connected",
            "session_id": session_id,
            "mode": f"{mode} {diarization_status}",
            "message": f"Ready ({mode} mode {diarization_status})"
        })
        
        audio_chunks = []
        
        while True:
            data = await websocket.receive()
            
            if "text" in data:
                try:
                    message = json.loads(data["text"])
                    if message.get("type") == "session_info":
                        doctor_name = message.get("doctor", "Unknown")
                        template_name = message.get("template", "default")
                        
                        # Get provider info
                        provider = get_provider_by_name(doctor_name)
                        if provider:
                            provider_id = provider['id']
                            use_voice_profile = provider.get('has_voice_profile', False)
                        
                        session = session_manager.get_session(session_id)
                        if session:
                            session['doctor'] = doctor_name
                            session['provider_id'] = provider_id
                            session['template'] = template_name
                            
                        logging.info(f"Session {session_id}: Provider={doctor_name}, Voice Profile={use_voice_profile}")
                except:
                    message = data["text"]
                    
                    if message == "END":
                        if audio_chunks:
                            await websocket.send_json({"status": "Converting audio..."})
                            
                            combined_audio = b''.join(audio_chunks)
                            audio_chunks = []
                            
                            wav_path = convert_audio_to_wav(combined_audio)
                            if not wav_path:
                                await websocket.send_json({"error": "Audio conversion failed"})
                                continue
                            
                            await websocket.send_json({
                                "status": f"Transcribing with speaker detection..."
                            })
                            
                            transcript = transcribe_audio_with_diarization(
                                wav_path, 
                                doctor_name,
                                use_voice_profile=use_voice_profile
                            )
                            
                            if wav_path and os.path.exists(wav_path):
                                os.unlink(wav_path)
                            
                            await websocket.send_json({
                                "transcript": transcript,
                                "status": "Generating SOAP note..."
                            })
                            
                            soap = generate_soap_note(transcript, template_name, doctor_name or "")
                            
                            save_session(
                                session_id, 
                                doctor_name or "Unknown", 
                                transcript, 
                                soap,
                                template=template_name,
                                provider_id=provider_id
                            )
                            
                            await websocket.send_json({
                                "transcript": transcript,
                                "soap": soap,
                                "status": "Complete"
                            })
                            
                            logging.info(f"Session {session_id}: Completed by {doctor_name}")
                    
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
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

# ============================================
# Session Management Endpoints
# ============================================

@app.get("/api/sessions")
async def get_sessions():
    """Get all sessions"""
    return get_all_sessions()

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get specific session"""
    session = get_session_by_id(session_id)
    if session:
        return session
    raise HTTPException(status_code=404, detail="Session not found")

@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, update_data: dict):
    """Update session data"""
    try:
        # For now, we'll just update the SOAP note
        # You can extend this to update other fields as needed
        soap_note = update_data.get('soap_note')
        
        if soap_note is not None:
            # Import the update function from database.py
            from database import update_session_soap
            success = update_session_soap(session_id, soap_note)
            
            if success:
                # Return the updated session
                session = get_session_by_id(session_id)
                return session
            else:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
    except Exception as e:
        logging.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    try:
        logging.info(f"Attempting to delete session: {session_id}")
        from database import delete_session_by_id
        success = delete_session_by_id(session_id)
        
        if success:
            logging.info(f"Session {session_id} deleted successfully")
            return {"message": "Session deleted successfully", "session_id": session_id}
        else:
            logging.warning(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@app.get("/api/sessions/provider/{provider_id}")
async def get_provider_sessions(provider_id: int):
    """Get all sessions for a specific provider"""
    return get_sessions_by_provider(provider_id)

# ============================================
# Template Management Endpoints
# ============================================

@app.get("/api/templates")
async def get_templates():
    """Get all available SOAP templates"""
    return template_manager.get_templates()

@app.get("/api/templates/list")
async def get_template_list():
    """Get list of templates with basic info"""
    return template_manager.get_template_list()

@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get specific template by ID"""
    template = template_manager.get_template(template_id)
    if template:
        return template
    raise HTTPException(status_code=404, detail="Template not found")

@app.post("/api/templates")
async def create_template(template_data: dict):
    """Create a new SOAP template"""
    try:
        template_id = template_data.get("id", "").lower().replace(" ", "_")
        name = template_data.get("name", "")
        description = template_data.get("description", "")
        ai_instructions = template_data.get("ai_instructions", "")
        sections = template_data.get("sections", {})
        
        if not template_id or not name or not sections:
            raise HTTPException(status_code=400, detail="Missing required fields: id, name, sections")
        
        # Check if template already exists
        if template_manager.get_template(template_id):
            raise HTTPException(status_code=409, detail="Template already exists")
        
        template = template_manager.create_custom_template(
            template_id, name, description, ai_instructions, sections
        )
        
        return {"status": "Template created successfully", "template": template}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@app.put("/api/templates/{template_id}")
async def update_template(template_id: str, template_data: dict):
    """Update an existing SOAP template"""
    try:
        logging.info(f"Updating template {template_id} with data: {template_data}")
        
        # Extract all fields from request
        name = template_data.get("name")
        description = template_data.get("description")
        ai_instructions = template_data.get("ai_instructions")
        sections = template_data.get("sections")
        
        logging.info(f"Template update parameters - Name: {name}, Description: {description}")
        logging.info(f"AI Instructions: {ai_instructions}")
        logging.info(f"Sections: {sections}")
        
        # Update template with all provided fields
        template = template_manager.update_template(
            template_id,
            name=name,
            description=description,
            ai_instructions=ai_instructions,
            sections=sections
        )
        
        if template:
            logging.info(f"Template {template_id} updated successfully: {template}")
            return {"status": "Template updated successfully", "template": template}
        else:
            logging.error(f"Template {template_id} not found")
            raise HTTPException(status_code=404, detail="Template not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to update template")

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a custom SOAP template"""
    try:
        success = template_manager.delete_template(template_id)
        if success:
            return {"status": "Template deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Cannot delete default template or template not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete template")

# ============================================
# SOAP Correction Endpoint
# ============================================

@app.post("/api/correct-soap")
async def correct_soap(request: CorrectionRequest):
    """Apply correction to SOAP note"""
    prompt = f"""You are updating a SOAP note based on the doctor's correction request.

Original SOAP Note:
{request.original_soap}

Original Transcript:
{request.transcript}

Correction Request: {request.correction}

Apply this correction to the SOAP note and return the complete updated SOAP note. Keep all sections (SUBJECTIVE, OBJECTIVE, ASSESSMENT, PLAN) intact and only modify what was requested. Maintain the same format and structure."""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30
        )
        if response.status_code == 200:
            corrected = response.json().get('response', request.original_soap)
            return {"corrected_soap": corrected}
    except Exception as e:
        logging.error(f"Correction error: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply correction")
    
    return {"corrected_soap": request.original_soap}

@app.post("/api/edit-soap-chat")
async def edit_soap_chat(request: SoapEditChatRequest):
    """Interactive chat-based SOAP note editing"""
    
    # Build chat context from history
    chat_context = ""
    if request.chat_history:
        chat_context = "\n\nRecent conversation:\n"
        for msg in request.chat_history[-3:]:  # Last 3 messages for context
            role = "Doctor" if msg.role == "user" else "AI Assistant"
            chat_context += f"{role}: {msg.content}\n"
    
    # Determine if this is a request to modify the SOAP note or just a question
    analysis_prompt = f"""Analyze this user message to determine if they want to modify the SOAP note or just ask a question:

User message: "{request.user_message}"

Respond with either "MODIFY" if they want to change the SOAP note, or "QUESTION" if they're just asking for information or clarification."""
    
    try:
        analysis_response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "llama3", "prompt": analysis_prompt, "stream": False},
            timeout=15
        )
        
        intent = "MODIFY"  # Default to modify
        if analysis_response.status_code == 200:
            analysis_result = analysis_response.json().get('response', '').strip().upper()
            if 'QUESTION' in analysis_result:
                intent = "QUESTION"
    except Exception as e:
        logging.error(f"Intent analysis error: {e}")
        intent = "MODIFY"  # Default to modify if analysis fails
    
    if intent == "QUESTION":
        # Handle question without modifying SOAP note
        question_prompt = f"""You are an AI assistant helping a doctor with their SOAP note. Answer their question helpfully and professionally.

Current SOAP Note:
{request.original_soap}

Original Transcript:
{request.transcript}

{chat_context}

Doctor's Question: {request.user_message}

Provide a helpful response. Do not modify the SOAP note unless explicitly asked."""
        
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": "llama3", "prompt": question_prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', 'I apologize, but I encountered an error processing your question.')
                return {
                    "ai_response": ai_response,
                    "updated_soap": request.original_soap,  # No changes
                    "soap_modified": False
                }
        except Exception as e:
            logging.error(f"Question handling error: {e}")
            return {
                "ai_response": "I apologize, but I encountered an error processing your question. Please try again.",
                "updated_soap": request.original_soap,
                "soap_modified": False
            }
    
    else:
        # Handle SOAP modification request
        modification_prompt = f"""You are a dental AI assistant helping to edit a SOAP note. The doctor wants to make changes based on their message.

Current SOAP Note:
{request.original_soap}

Original Transcript (for reference):
{request.transcript}

{chat_context}

Doctor's Request: {request.user_message}

Please:
1. Make the requested changes to the SOAP note
2. Maintain the proper SOAP format (SUBJECTIVE, OBJECTIVE, ASSESSMENT, PLAN)
3. Keep all existing information unless specifically asked to remove it
4. Use proper dental terminology and tooth numbering (1-32)
5. Provide both the updated SOAP note and a brief explanation of what you changed

Format your response as:
UPDATED_SOAP_NOTE:
[The complete updated SOAP note here]

EXPLANATION:
[Brief explanation of changes made]"""
        
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": "llama3", "prompt": modification_prompt, "stream": False},
                timeout=30
            )
            
            if response.status_code == 200:
                full_response = response.json().get('response', '')
                
                # Parse the response to extract SOAP note and explanation
                if "UPDATED_SOAP_NOTE:" in full_response and "EXPLANATION:" in full_response:
                    parts = full_response.split("EXPLANATION:")
                    soap_part = parts[0].replace("UPDATED_SOAP_NOTE:", "").strip()
                    explanation_part = parts[1].strip() if len(parts) > 1 else "SOAP note updated as requested."
                    
                    return {
                        "ai_response": explanation_part,
                        "updated_soap": soap_part,
                        "soap_modified": True
                    }
                else:
                    # Fallback if format isn't followed
                    return {
                        "ai_response": "I've updated the SOAP note based on your request.",
                        "updated_soap": full_response,
                        "soap_modified": True
                    }
                    
        except Exception as e:
            logging.error(f"SOAP modification error: {e}")
            return {
                "ai_response": f"I apologize, but I encountered an error modifying the SOAP note: {str(e)}. Please try rephrasing your request.",
                "updated_soap": request.original_soap,
                "soap_modified": False
            }
    
    # Fallback response
    return {
        "ai_response": "I apologize, but I couldn't process your request. Please try again.",
        "updated_soap": request.original_soap,
        "soap_modified": False
    }

# ============================================
# Health & Status Endpoints
# ============================================

@app.get("/")
async def root():
    return {
        "service": "Boise Prosthodontics AI Scribe",
        "whisper": "enabled" if WHISPER_AVAILABLE else "disabled",
        "diarization": "enabled" if DIARIZATION_AVAILABLE else "disabled",
        "voice_profiles": "enabled",
        "model": WHISPER_MODEL_SIZE if WHISPER_AVAILABLE else "none",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    ollama_status = "unknown"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        ollama_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy",
        "whisper": "enabled" if WHISPER_AVAILABLE else "disabled",
        "diarization": "enabled" if DIARIZATION_AVAILABLE else "disabled",
        "voice_profiles": "enabled",
        "ollama": ollama_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/regenerate_soap")
async def regenerate_soap(request: dict):
    """Regenerate SOAP note with a different template"""
    try:
        session_id = request.get("session_id")
        transcript = request.get("transcript") 
        template = request.get("template")
        doctor = request.get("doctor")
        
        if not all([session_id, transcript, template, doctor]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Generate new SOAP note using existing function
        soap_note = generate_soap_note(transcript, template, doctor)
        
        # Update session SOAP note
        update_session_soap(session_id, soap_note)
        
        # Update session template used 
        update_session_template(session_id, template)
        
        return {
            "soap_note": soap_note,
            "template_used": template,
            "status": "success"
        }
        
    except Exception as e:
        logging.error(f"Error regenerating SOAP note: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate SOAP note: {str(e)}")

# ============================================
# Email and Patient Management Endpoints
# ============================================

@app.post("/api/generate-post-visit-email")
async def generate_post_visit_email_endpoint(request: EmailGenerationRequest):
    """Generate AI-powered post-visit summary email"""
    try:
        email_result = generate_post_visit_email(
            soap_note=request.soap_note,
            patient_name=request.patient_name,
            provider_name=request.provider_name,
            appointment_date=request.appointment_date,
            transcript=request.transcript
        )
        return email_result
    except Exception as e:
        logging.error(f"Email generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")

@app.post("/api/lookup-patient")
async def lookup_patient_endpoint(request: PatientLookupRequest):
    """Lookup patient information from Dentrix API"""
    try:
        patient_results = await lookup_patient_dentrix(request)
        return patient_results
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Patient lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Patient lookup failed: {str(e)}")

@app.post("/api/send-patient-email")
async def send_patient_email_endpoint(request: PostVisitEmailRequest):
    """Send post-visit summary email to patient"""
    try:
        result = await send_patient_email(request)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/api/decrypt-patient-data")
async def decrypt_patient_data_endpoint(encrypted_data: dict):
    """Decrypt patient data for display (temporary endpoint for UI)"""
    try:
        decrypted = {}
        for key, value in encrypted_data.items():
            if key in ['email', 'phone'] and value:
                try:
                    decrypted[key] = encryption_manager.decrypt_data(value)
                except:
                    decrypted[key] = value  # If not encrypted, return as is
            elif key == 'address' and value:
                decrypted[key] = {}
                for addr_key, addr_value in value.items():
                    if addr_key in ['street', 'zip'] and addr_value:
                        try:
                            decrypted[key][addr_key] = encryption_manager.decrypt_data(addr_value)
                        except:
                            decrypted[key][addr_key] = addr_value
                    else:
                        decrypted[key][addr_key] = addr_value
            else:
                decrypted[key] = value
        return decrypted
    except Exception as e:
        logging.error(f"Decryption error: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt patient data")

# ============================================
# Configuration Management Endpoints
# ============================================

@app.get("/api/config")
async def get_config():
    """Get current configuration settings (without sensitive data)"""
    try:
        return {
            "email": {
                "smtp_server": os.getenv('SMTP_SERVER', ''),
                "smtp_port": os.getenv('SMTP_PORT', '587'),
                "smtp_username": os.getenv('SMTP_USERNAME', ''),
                "configured": bool(os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD'))
            },
            "dentrix": {
                "api_url": os.getenv('DENTRIX_API_URL', ''),
                "configured": bool(os.getenv('DENTRIX_API_KEY'))
            },
            "ai": {
                "ollama_host": os.getenv('OLLAMA_HOST', 'http://ollama:11434'),
                "whisper_model": os.getenv('WHISPER_MODEL', 'tiny')
            }
        }
    except Exception as e:
        logging.error(f"Config retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")

@app.post("/api/config/email")
async def update_email_config(config: dict):
    """Update email configuration"""
    try:
        # Update environment variables
        if 'smtp_server' in config:
            os.environ['SMTP_SERVER'] = config['smtp_server']
        if 'smtp_port' in config:
            os.environ['SMTP_PORT'] = str(config['smtp_port'])
        if 'smtp_username' in config:
            os.environ['SMTP_USERNAME'] = config['smtp_username']
        if 'smtp_password' in config:
            os.environ['SMTP_PASSWORD'] = config['smtp_password']
        
        # Update .env file
        env_path = Path('.env')
        env_lines = []
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add configuration lines
        config_map = {
            'SMTP_SERVER': config.get('smtp_server', ''),
            'SMTP_PORT': str(config.get('smtp_port', '587')),
            'SMTP_USERNAME': config.get('smtp_username', ''),
            'SMTP_PASSWORD': config.get('smtp_password', '')
        }
        
        updated_lines = []
        updated_keys = set()
        
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in config_map:
                    updated_lines.append(f"{key}={config_map[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add new keys that weren't in the file
        for key, value in config_map.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}\n")
        
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        return {"status": "success", "message": "Email configuration updated"}
        
    except Exception as e:
        logging.error(f"Email config update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update email configuration")

@app.post("/api/config/dentrix")
async def update_dentrix_config(config: dict):
    """Update Dentrix API configuration"""
    try:
        # Update environment variables
        if 'api_url' in config:
            os.environ['DENTRIX_API_URL'] = config['api_url']
        if 'api_key' in config:
            os.environ['DENTRIX_API_KEY'] = config['api_key']
        
        # Update .env file
        env_path = Path('.env')
        env_lines = []
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        config_map = {
            'DENTRIX_API_URL': config.get('api_url', ''),
            'DENTRIX_API_KEY': config.get('api_key', '')
        }
        
        updated_lines = []
        updated_keys = set()
        
        for line in env_lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in config_map:
                    updated_lines.append(f"{key}={config_map[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add new keys
        for key, value in config_map.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}\n")
        
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        return {"status": "success", "message": "Dentrix configuration updated"}
        
    except Exception as e:
        logging.error(f"Dentrix config update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update Dentrix configuration")

@app.post("/api/config/ai")
async def update_ai_config(config: dict):
    """Update AI/Ollama configuration"""
    try:
        global OLLAMA_HOST
        
        if 'ollama_host' in config:
            new_host = config['ollama_host']
            
            # Test the connection first
            try:
                test_response = requests.get(f"{new_host}/api/tags", timeout=5)
                if test_response.status_code != 200:
                    return {"status": "error", "message": "Cannot connect to Ollama at specified host"}
            except:
                return {"status": "error", "message": "Cannot reach Ollama server"}
            
            # Update environment variable
            os.environ['OLLAMA_HOST'] = new_host
            OLLAMA_HOST = new_host
            
            # Update .env file
            env_path = Path('../.env')
            env_lines = []
            
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            updated = False
            for i, line in enumerate(env_lines):
                if line.startswith('OLLAMA_HOST='):
                    env_lines[i] = f'OLLAMA_HOST={new_host}\n'
                    updated = True
                    break
            
            if not updated:
                env_lines.append(f'OLLAMA_HOST={new_host}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
            
            return {"status": "success", "message": "Ollama configuration updated", "ollama_host": new_host}
        
        return {"status": "error", "message": "No configuration provided"}
        
    except Exception as e:
        logging.error(f"AI config update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update AI configuration")

@app.post("/api/config/test-ollama")
async def test_ollama_config():
    """Test Ollama connection"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json()
            return {
                "status": "success",
                "message": "Successfully connected to Ollama",
                "host": OLLAMA_HOST,
                "models": models.get('models', [])
            }
        else:
            return {
                "status": "error",
                "message": f"Ollama returned status {response.status_code}",
                "host": OLLAMA_HOST
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": f"Cannot connect to Ollama at {OLLAMA_HOST}",
            "host": OLLAMA_HOST
        }
    except Exception as e:
        logging.error(f"Ollama test error: {e}")
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "host": OLLAMA_HOST
        }

@app.post("/api/config/test-email")
async def test_email_config():
    """Test email configuration by sending a test email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_server, smtp_username, smtp_password]):
            raise HTTPException(status_code=400, detail="Email configuration incomplete")
        
        # Create test message
        msg = MIMEText("This is a test email from Boise Prosthodontics AI Scribe system.")
        msg['Subject'] = 'Test Email - AI Scribe System'
        msg['From'] = smtp_username
        msg['To'] = smtp_username  # Send to self for testing
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        return {"status": "success", "message": "Test email sent successfully"}
        
    except Exception as e:
        logging.error(f"Test email error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

@app.post("/api/config/test-dentrix")
async def test_dentrix_config():
    """Test Dentrix API configuration"""
    try:
        api_url = os.getenv('DENTRIX_API_URL')
        api_key = os.getenv('DENTRIX_API_KEY')
        
        if not all([api_url, api_key]):
            raise HTTPException(status_code=400, detail="Dentrix configuration incomplete")
        
        # Test API connection
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{api_url}/patients/test",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {"status": "success", "message": "Dentrix API connection successful"}
        else:
            return {"status": "error", "message": f"Dentrix API returned status {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Dentrix test error: {e}")
        return {"status": "error", "message": f"Failed to connect to Dentrix API: {str(e)}"}
    except Exception as e:
        logging.error(f"Dentrix config test error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test Dentrix configuration: {str(e)}")

# AI Training and Knowledge Base Endpoints
@app.get("/api/knowledge-articles")
async def get_knowledge_articles():
    """Get all knowledge articles"""
    try:
        from database import get_all_knowledge_articles
        articles = get_all_knowledge_articles()
        return articles
    except Exception as e:
        logging.error(f"Error fetching knowledge articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge articles")

@app.post("/api/knowledge-articles")
async def create_knowledge_article_endpoint(article: KnowledgeArticle):
    """Create a new knowledge article"""
    try:
        from database import create_knowledge_article
        result = create_knowledge_article(
            title=article.title,
            content=article.content,
            category=article.category
        )
        if result:
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to create knowledge article")
    except Exception as e:
        logging.error(f"Error creating knowledge article: {e}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge article")

@app.delete("/api/knowledge-articles/{article_id}")
async def delete_knowledge_article_endpoint(article_id: str):
    """Delete a knowledge article"""
    try:
        from database import delete_knowledge_article
        result = delete_knowledge_article(article_id)
        if result:
            return {"message": "Article deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Article not found")
    except Exception as e:
        logging.error(f"Error deleting knowledge article: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge article")

@app.put("/api/knowledge-articles/{article_id}")
async def update_knowledge_article_endpoint(article_id: str, article: KnowledgeArticle):
    """Update a knowledge article"""
    try:
        from database import update_knowledge_article
        result = update_knowledge_article(
            article_id=article_id,
            title=article.title,
            content=article.content,
            category=article.category
        )
        if result:
            return result
        else:
            raise HTTPException(status_code=404, detail="Article not found")
    except Exception as e:
        logging.error(f"Error updating knowledge article: {e}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge article")

@app.post("/api/ai-training/chat")
async def ai_training_chat(request: TrainingChatRequest):
    """Chat with AI for training purposes"""
    try:
        # Get relevant knowledge articles for context
        from database import get_all_knowledge_articles
        knowledge_articles = get_all_knowledge_articles()
        
        # Create context from knowledge base
        knowledge_context = ""
        if knowledge_articles:
            knowledge_context = "\n\nKnowledge Base Context:\n"
            for article in knowledge_articles[:5]:  # Limit to 5 most relevant
                knowledge_context += f"- {article['title']} ({article['category']}): {article['content'][:200]}...\n"
        
        # Enhanced training prompt
        training_prompt = f"""You are an AI assistant for a dental prosthodontics practice. The user is training you to be a better dental scribe and assistant.

User message: {request.message}

{knowledge_context}

Please respond as a helpful, knowledgeable dental assistant. If the user is providing feedback or training, acknowledge it and explain how you'll incorporate their guidance. If they're asking a question, provide accurate dental information based on your knowledge and the context provided.

Focus on:
1. Dental prosthodontics knowledge
2. SOAP note documentation
3. Patient care best practices
4. Treatment planning
5. Post-operative instructions

Respond in a professional, helpful manner:"""

        # Send to Ollama
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": "llama3",
                    "prompt": training_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '').strip()
                
                return {"response": ai_response}
            else:
                return {"response": "I'm having trouble processing your message right now. Please try again."}
                
        except requests.exceptions.Timeout:
            return {"response": "I'm taking longer than usual to respond. Please try again."}
        except Exception as e:
            logging.error(f"Ollama error in training chat: {e}")
            return {"response": "I encountered an error. Please try again."}
            
    except Exception as e:
        logging.error(f"AI training chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process training chat")

if __name__ == "__main__":
    import uvicorn
    print("Starting Boise Prosthodontics AI Scribe...")
    print(f"Whisper: {'Enabled' if WHISPER_AVAILABLE else 'Mock Mode'}")
    print(f"Diarization: {'Enabled' if DIARIZATION_AVAILABLE else 'Single Speaker Mode'}")
    print(f"Ollama: {OLLAMA_HOST}")
    uvicorn.run(app, host="0.0.0.0", port=3051)