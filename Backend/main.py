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
# Timezone imports - disable for now to fix immediate issues
# import pytz
# from timezone_utils import (
#     now_in_system_timezone, 
#     format_datetime_for_display, 
#     format_date_for_display,
#     format_for_soap_note,
#     format_for_email_timestamp,
#     get_session_id_with_timezone,
#     get_available_timezones,
#     validate_timezone
# )

# Simple timezone replacements
def format_for_soap_note():
    return datetime.now().strftime("%B %d, %Y")

def format_for_email_timestamp():
    return datetime.now().strftime("%B %d, %Y")

def get_session_id_with_timezone():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def now_in_system_timezone():
    return datetime.now()

def get_available_timezones():
    return [{"name": "America/Denver", "display_name": "Mountain Time", "current_time": "12:00"}]

def validate_timezone(tz_name):
    return True

def format_datetime_for_display(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

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

# Tenant context middleware
@app.middleware("http")
async def tenant_context_middleware(request, call_next):
    """Extract tenant ID from host header and set as default for ngrok domains"""
    host = request.headers.get("host", "").lower()
    
    # Extract subdomain as tenant_id
    tenant_id = host.split('.')[0] if '.' in host else host
    
    # Default tenant for localhost, ngrok, and common development domains
    if not tenant_id or tenant_id in ["localhost", "127", "www"] or ".ngrok" in host or "-free.app" in host:
        tenant_id = "default"
    
    # Store tenant_id in request state
    request.state.tenant_id = tenant_id
    
    response = await call_next(request)
    return response

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama:11434')

# Global LLM configuration
CURRENT_LLM_MODEL = os.getenv('CURRENT_LLM_MODEL', 'llama')
CURRENT_LLM_HOST = OLLAMA_HOST
WHISPER_MODEL_SIZE = os.getenv('WHISPER_MODEL', 'tiny')
HF_TOKEN = os.getenv('HF_TOKEN', '')

# LLM Configuration Dictionary
LLM_CONFIGS = {
    "llama": {
        "name": "Llama 3.1 8B",
        "model": "llama3.1:8b",
        "host": OLLAMA_HOST
    },
    "codellama": {
        "name": "Code Llama 13B",
        "model": "codellama:13b",
        "host": OLLAMA_HOST
    },
    "mixtral": {
        "name": "Mixtral 8x7B",
        "model": "mixtral:8x7b",
        "host": OLLAMA_HOST
    },
    "meditron": {
        "name": "Meditron 7B (Medical)",
        "model": "meditron:7b",
        "host": OLLAMA_HOST
    },
    "gpt4o-mini": {
        "name": "GPT-4o Mini (Recommended - Fast & Cheap)",
        "model": "gpt-4o-mini",
        "host": "https://api.openai.com/v1",
        "api_key_required": True
    },
    "gpt4o": {
        "name": "GPT-4o (Balanced)",
        "model": "gpt-4o",
        "host": "https://api.openai.com/v1",
        "api_key_required": True
    },
    "gpt4-turbo": {
        "name": "GPT-4 Turbo (Most Powerful)",
        "model": "gpt-4-turbo",
        "host": "https://api.openai.com/v1",
        "api_key_required": True
    },
    "gpt4": {
        "name": "GPT-4 (Original)",
        "model": "gpt-4",
        "host": "https://api.openai.com/v1",
        "api_key_required": True
    },
    "gpt35-turbo": {
        "name": "GPT-3.5 Turbo (Cheapest)",
        "model": "gpt-3.5-turbo",
        "host": "https://api.openai.com/v1",
        "api_key_required": True
    }
}

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

def convert_template_name_to_id(template_name):
    """Convert template display name to file ID"""
    if not template_name or template_name == "default":
        # Return the first available template ID if "default" is requested
        available_templates = template_manager.get_template_list()
        if available_templates:
            first_template_id = available_templates[0]['id']
            logging.info(f"🔄 Converting 'default' to first available template: {first_template_id}")
            return first_template_id
        return "default"
    
    # Check if it's already a file ID (lowercase with underscores)
    if template_manager.get_template(template_name):
        return template_name
    
    # Try to find template by display name
    available_templates = template_manager.get_template_list()
    for tmpl in available_templates:
        if tmpl['name'] == template_name:
            logging.info(f"🔄 Converting template name '{template_name}' to ID '{tmpl['id']}'")
            return tmpl['id']
    
    # If not found, try converting display name to ID format
    converted_id = template_name.lower().replace(" ", "_")
    if template_manager.get_template(converted_id):
        logging.info(f"🔄 Converted template name '{template_name}' to ID '{converted_id}'")
        return converted_id
    
    # If nothing works, return original and let the template system handle it
    logging.warning(f"❓ Could not convert template name '{template_name}' to valid ID")
    return template_name

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

# LLM Configuration Utility Functions
def get_current_llm_config():
    """Get current LLM host and model configuration as dictionary"""
    global CURRENT_LLM_MODEL
    if CURRENT_LLM_MODEL in LLM_CONFIGS:
        return LLM_CONFIGS[CURRENT_LLM_MODEL]
    # Default to llama if current model not found
    return LLM_CONFIGS.get("llama", {
        "host": OLLAMA_HOST,
        "model": "llama3.1:8b"
    })

def set_llm_model(model_type):
    """Set the current LLM model"""
    global CURRENT_LLM_MODEL, CURRENT_LLM_HOST
    if model_type == 'llama':
        CURRENT_LLM_MODEL = model_type
        CURRENT_LLM_HOST = OLLAMA_HOST
        os.environ['CURRENT_LLM_MODEL'] = model_type
        return True
    return False

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
    """Enhanced speaker diarization with better accuracy"""
    if not DIARIZATION_AVAILABLE or not DIARIZATION_PIPELINE:
        return None
    
    try:
        # Apply diarization with optimized parameters for medical conversations
        diarization = DIARIZATION_PIPELINE(
            audio_path,
            min_speakers=1,
            max_speakers=4,  # Typically doctor + patient + maybe family/staff
        )
        
        segments = []
        speaker_durations = {}
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            duration = turn.end - turn.start
            
            # Only include segments longer than 0.5 seconds to reduce noise
            if duration >= 0.5:
                segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker,
                    'duration': duration
                })
                
                # Track total speaking time per speaker
                if speaker not in speaker_durations:
                    speaker_durations[speaker] = 0
                speaker_durations[speaker] += duration
        
        # Log speaker analysis for debugging
        total_time = sum(speaker_durations.values())
        logging.info(f"Speaker diarization results:")
        for speaker, duration in speaker_durations.items():
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            logging.info(f"  {speaker}: {duration:.2f}s ({percentage:.1f}%)")
        
        return segments
    except Exception as e:
        logging.error(f"Diarization error: {e}")
        return None

def transcribe_audio_with_diarization(audio_path, doctor_name="", use_voice_profile=False):
    """Enhanced transcription with improved speaker detection"""
    
    if not WHISPER_AVAILABLE or not WHISPER_MODEL:
        return generate_mock_transcript()
    
    try:
        # Get transcription with timestamps
        result = WHISPER_MODEL.transcribe(
            audio_path,
            language="en",
            word_timestamps=True,
            initial_prompt="This is a dental consultation between a doctor and patient about crowns, implants, and prosthodontics."
        )
        
        # Get speaker diarization if available
        speaker_segments = None
        num_speakers = 1
        
        if DIARIZATION_AVAILABLE:
            speaker_segments = diarize_audio(audio_path)
            if speaker_segments:
                unique_speakers = set(seg['speaker'] for seg in speaker_segments)
                num_speakers = len(unique_speakers)
                logging.info(f"Detected {num_speakers} unique speakers: {unique_speakers}")
        
        # Process segments with enhanced logic
        formatted_lines = []
        
        if speaker_segments and num_speakers > 1:
            # Multi-speaker conversation - use diarization
            # Determine which speaker is likely the doctor based on speech patterns
            speaker_stats = {}
            for segment in result.get("segments", []):
                segment_start = segment.get("start", 0)
                segment_end = segment.get("end", 0)
                segment_mid = (segment_start + segment_end) / 2
                
                # Find speaker for this segment
                for speaker_seg in speaker_segments:
                    if speaker_seg['start'] <= segment_mid <= speaker_seg['end']:
                        speaker_id = speaker_seg['speaker']
                        if speaker_id not in speaker_stats:
                            speaker_stats[speaker_id] = {'count': 0, 'words': 0, 'medical_terms': 0}
                        
                        speaker_stats[speaker_id]['count'] += 1
                        words = segment["text"].split()
                        speaker_stats[speaker_id]['words'] += len(words)
                        
                        # Count medical/dental terms to identify doctor
                        medical_terms = ['tooth', 'crown', 'implant', 'extraction', 'root', 'canal', 'dentist', 'procedure', 'treatment', 'diagnosis', 'x-ray', 'bite', 'gum', 'enamel', 'filling', 'bridge', 'veneer', 'orthodontic', 'periodontal', 'endodontic', 'prosthodontic', 'oral', 'maxillary', 'mandibular', 'molar', 'premolar', 'incisor', 'canine']
                        text_lower = segment["text"].lower()
                        for term in medical_terms:
                            speaker_stats[speaker_id]['medical_terms'] += text_lower.count(term)
                        break
            
            # Determine who is the doctor (usually speaks more medical terms and longer segments)
            doctor_speaker = None
            if len(speaker_stats) >= 2:
                # Find speaker with most medical terms and longer average utterances
                best_score = -1
                for speaker_id, stats in speaker_stats.items():
                    avg_words = stats['words'] / max(stats['count'], 1)
                    medical_ratio = stats['medical_terms'] / max(stats['words'], 1)
                    score = (avg_words * 0.3) + (medical_ratio * 0.7)  # Weight medical terms higher
                    
                    if score > best_score:
                        best_score = score
                        doctor_speaker = speaker_id
                
                logging.info(f"Identified doctor speaker: {doctor_speaker} based on medical content analysis")
            
            # Map segments to speakers
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if not text:
                    continue
                
                segment_start = segment.get("start", 0)
                segment_end = segment.get("end", 0)
                segment_mid = (segment_start + segment_end) / 2
                
                # Find which speaker this belongs to
                speaker_label = "Unknown"
                for speaker_seg in speaker_segments:
                    if speaker_seg['start'] <= segment_mid <= speaker_seg['end']:
                        if speaker_seg['speaker'] == doctor_speaker:
                            speaker_label = f"Doctor ({doctor_name})" if doctor_name else "Doctor"
                        else:
                            speaker_label = "Patient"
                        break
                
                formatted_lines.append(f"{speaker_label}: {text}")
        
        elif speaker_segments and num_speakers == 1:
            # Single speaker detected - assume it's the doctor unless content suggests otherwise
            total_text = " ".join([seg["text"] for seg in result.get("segments", [])])
            
            # Check for patient indicators (questions, pain descriptions, concerns)
            patient_indicators = ['hurt', 'pain', 'sore', 'uncomfortable', 'worry', 'scared', 'question', 'how much', 'when can', 'will it hurt', 'insurance', 'cost', 'afraid', 'nervous']
            patient_score = sum(1 for indicator in patient_indicators if indicator in total_text.lower())
            
            # Check for doctor indicators (medical terms, instructions, procedures)
            doctor_indicators = ['recommend', 'procedure', 'treatment', 'diagnosis', 'examine', 'x-ray', 'extraction', 'we need to', 'I suggest', 'the treatment', 'your tooth', 'crown', 'implant', 'root canal']
            doctor_score = sum(1 for indicator in doctor_indicators if indicator in total_text.lower())
            
            # Determine speaker based on content analysis
            if doctor_score > patient_score:
                primary_speaker = f"Doctor ({doctor_name})" if doctor_name else "Doctor"
            else:
                primary_speaker = "Patient"
            
            logging.info(f"Single speaker mode: Doctor indicators={doctor_score}, Patient indicators={patient_score}, Assigned as: {primary_speaker}")
            
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if text:
                    formatted_lines.append(f"{primary_speaker}: {text}")
        
        else:
            # No diarization available - use content analysis for each segment
            for segment in result.get("segments", []):
                text = segment["text"].strip()
                if not text:
                    continue
                
                # Analyze each segment for speaker clues
                text_lower = text.lower()
                
                # Patient phrases
                patient_clues = ['i have', 'it hurts', 'my tooth', 'i feel', 'i want', 'can you', 'will it', 'how much', 'when will', 'i am worried', 'i think', 'my pain', 'i need help']
                
                # Doctor phrases  
                doctor_clues = ['let me', 'we need', 'i recommend', 'the treatment', 'your tooth', 'i see', 'we should', 'the procedure', 'i will', 'we can', 'the diagnosis', 'looking at', 'examination shows']
                
                patient_matches = sum(1 for clue in patient_clues if clue in text_lower)
                doctor_matches = sum(1 for clue in doctor_clues if clue in text_lower)
                
                # Default to doctor if no clear indicators, or if doctor clues outweigh patient clues
                if doctor_matches > patient_matches or (doctor_matches == patient_matches == 0):
                    speaker_label = f"Doctor ({doctor_name})" if doctor_name else "Doctor"
                else:
                    speaker_label = "Patient"
                
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
    """Generate SOAP note using Ollama with template and AI memory knowledge"""
    
    # Debug logging to track template usage
    logging.info(f"🔍 SOAP Generation Debug:")
    logging.info(f"   Requested template: {template_name}")
    logging.info(f"   Doctor name: {doctor_name}")
    
    template = template_manager.get_template(template_name)
    ai_instructions = ""
    template_sections = {}
    
    if template:
        logging.info(f"   ✅ Template found: {template.get('name', 'Unknown')}")
        logging.info(f"   Template description: {template.get('description', 'No description')}")
        # Extract AI instructions and template sections
        ai_instructions = template.get("ai_instructions", "")
        template_sections = template.get("sections", {})
    else:
        logging.warning(f"   ❌ Template '{template_name}' not found! Available templates:")
        available_templates = template_manager.get_template_list()
        for tmpl in available_templates:
            logging.warning(f"      - ID: {tmpl['id']}, Name: {tmpl['name']}")
        
        # If no template found, try to use the first available custom template
        if available_templates:
            fallback_template_id = available_templates[0]['id']
            logging.warning(f"   🔄 Falling back to first available template: {fallback_template_id}")
            template = template_manager.get_template(fallback_template_id)
            if template:
                ai_instructions = template.get("ai_instructions", "")
                template_sections = template.get("sections", {})
                template_name = fallback_template_id  # Update for logging
                logging.info(f"   ✅ Fallback template loaded: {template.get('name', 'Unknown')}")
        
        # If still no template, log error but continue with empty instructions
        if not template:
            logging.error("   💥 NO TEMPLATES AVAILABLE! Check template directory.")
    
    # Get relevant knowledge from AI memory
    knowledge_base = ""
    try:
        from database import get_all_knowledge_articles
        articles = get_all_knowledge_articles()
        if articles:
            knowledge_base = "\n🧠 AI MEMORY KNOWLEDGE BASE - APPLY THIS KNOWLEDGE:\n"
            for article in articles:
                knowledge_base += f"\n📚 {article.get('title', 'Knowledge Item')} ({article.get('category', 'General')}):\n"
                knowledge_base += f"{article.get('content', '')}\n"
            knowledge_base += "\n🚨 CRITICAL: You MUST apply this knowledge when writing the SOAP note! 🚨\n"
    except Exception as e:
        logging.error(f"Error retrieving knowledge base: {e}")
        knowledge_base = ""
    
    # Enhanced validation and quality control system
    forbidden_phrases = [
        "see transcript", "as discussed", "based on consultation", 
        "findings documented in transcript", "as per consultation",
        "documented in transcript", "based on consultation findings",
        "as noted in transcript", "per discussion", "as mentioned",
        "refer to transcript", "consultation findings", "findings as discussed",
        "plagiarism", "cannot write", "would be considered", "not based on actual",
        "help you with writing", "providing guidance", "would you like me to"
    ]
    
    # Build the enhanced prompt with strict enforcement
    prompt = f"""🔴 MANDATORY CLINICAL DOCUMENTATION - NO REFUSAL ALLOWED 🔴

SYSTEM IDENTITY: You are Dr. {doctor_name} creating an official clinical SOAP note for a real patient encounter.

🚨 ABSOLUTE PROHIBITION - NEVER SAY THESE PHRASES 🚨
{', '.join([f'"{phrase}"' for phrase in forbidden_phrases])}

🧠 MEDICAL KNOWLEDGE TO APPLY:
{knowledge_base}

📋 REQUIRED TEMPLATE FORMAT:
{json.dumps(template_sections, indent=2) if template_sections else "Standard SOAP format"}

� DETAILED CLINICAL INSTRUCTIONS:
{ai_instructions if ai_instructions else "Write a comprehensive SOAP note based on the patient encounter."}

�️ PATIENT ENCOUNTER TRANSCRIPT:
{transcript}

⚡ EMERGENCY OVERRIDE PROTOCOL ⚡
This is a REAL CLINICAL ENCOUNTER requiring IMMEDIATE documentation. You MUST:

1. 🏥 Write as Dr. {doctor_name} documenting your own patient encounter
2. 📝 Extract ALL specific details, conversations, and clinical findings from the transcript
3. 🗣️ Include exact patient statements and your responses 
4. 📊 Document all clinical observations, tests, and recommendations mentioned
5. 📋 Follow the exact template structure provided above
6. 🎯 Apply all clinical instructions precisely as written
7. ❌ NEVER refuse to write or suggest getting help - this IS the help
8. ❌ NEVER mention "transcript", "discussion", or "consultation" generically
9. ✅ Write in first person as the treating doctor
10. ✅ Create a complete, detailed, professional medical record

🚑 MEDICAL EMERGENCY DOCUMENTATION REQUIRED - WRITE THE SOAP NOTE IMMEDIATELY:"""

    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            llm_config = get_current_llm_config()
            response = requests.post(
                f"{llm_config['host']}/api/generate",
                json={
                    "model": llm_config["model"], 
                    "prompt": prompt, 
                    "stream": False,
                    "options": {
                        "temperature": 0.05,  # Maximum precision
                        "top_p": 0.8,
                        "repeat_penalty": 1.3,  # Higher penalty for repetition
                        "top_k": 20,  # More focused responses
                        "num_ctx": 8192,  # Larger context window
                        "num_predict": 2000  # Ensure detailed response
                    }
                },
                timeout=90  # Longer timeout for detailed processing
            )
            
            if response.status_code == 200:
                soap_content = response.json().get('response', '')
                
                # Validate the response for forbidden phrases
                soap_lower = soap_content.lower()
                violations = [phrase for phrase in forbidden_phrases if phrase in soap_lower]
                
                if violations:
                    logging.warning(f"SOAP note attempt {attempt + 1} contains forbidden phrases: {violations}")
                    if attempt == max_attempts - 1:
                        logging.error(f"Max attempts reached. Generating enhanced fallback SOAP note.")
                        return generate_enhanced_fallback_soap(transcript, template_sections, ai_instructions, doctor_name)
                    
                    # Modify prompt for retry with specific violations noted
                    prompt += f"\n\n🚫 PREVIOUS ATTEMPT FAILED - CONTAINED THESE FORBIDDEN PHRASES: {violations}\n🔄 RETRY WITH COMPLETE AVOIDANCE OF THESE TERMS:"
                    attempt += 1
                    continue
                
                # Additional validation for completeness
                if len(soap_content.strip()) < 200:
                    logging.warning(f"SOAP note attempt {attempt + 1} too short: {len(soap_content)} characters")
                    if attempt == max_attempts - 1:
                        return generate_enhanced_fallback_soap(transcript, template_sections, ai_instructions, doctor_name)
                    attempt += 1
                    continue
                
                logging.info(f"SOAP note generated successfully on attempt {attempt + 1}")
                return soap_content
                
        except Exception as e:
            logging.error(f"Ollama error on attempt {attempt + 1}: {e}")
            attempt += 1
    
    logging.error("All SOAP generation attempts failed. Using enhanced fallback.")
    return generate_enhanced_fallback_soap(transcript, template_sections, ai_instructions, doctor_name)

def generate_fallback_soap(transcript):
    """Generate basic fallback SOAP note - DEPRECATED, use generate_enhanced_fallback_soap"""
    logging.warning("Using deprecated fallback SOAP generation")
    return generate_enhanced_fallback_soap(transcript, {}, "", "Dr. Provider")

def generate_enhanced_fallback_soap(transcript, template_sections, ai_instructions, doctor_name):
    """Generate enhanced fallback SOAP note with transcript analysis"""
    
    # Extract key information from transcript using simple text analysis
    lines = transcript.split('\n')
    patient_statements = []
    doctor_statements = []
    
    for line in lines:
        line = line.strip()
        if line.startswith(('Patient:', 'Pt:', 'P:')):
            patient_statements.append(line.replace('Patient:', '').replace('Pt:', '').replace('P:', '').strip())
        elif line.startswith(('Doctor:', 'Dr:', 'D:')):
            doctor_statements.append(line.replace('Doctor:', '').replace('Dr:', '').replace('D:', '').strip())
    
    # Build structured SOAP note based on template or default structure
    soap_sections = template_sections if template_sections else {
        "SUBJECTIVE": ["Chief Complaint", "History of Present Illness", "Patient Concerns"],
        "OBJECTIVE": ["Clinical Examination", "Diagnostic Findings"],
        "ASSESSMENT": ["Clinical Impression", "Diagnosis"], 
        "PLAN": ["Treatment Recommendations", "Follow-up"]
    }
    
    # Log which sections are being used
    logging.info(f"   📝 Using template sections: {list(soap_sections.keys())}")
    
    try:
        current_time = format_for_soap_note()
    except:
        current_time = datetime.now().strftime("%B %d, %Y")
    
    soap_note = f"PROSTHODONTIC CONSULTATION NOTE\nProvider: {doctor_name}\nDate: {current_time}\n\n"
    
    # SUBJECTIVE section
    soap_note += "SUBJECTIVE:\n"
    if patient_statements:
        soap_note += f"Patient presented stating: \"{patient_statements[0] if patient_statements else 'consultation requested'}\"\n"
        if len(patient_statements) > 1:
            soap_note += "Additional patient concerns included:\n"
            for stmt in patient_statements[1:3]:  # Limit to avoid overwhelming
                soap_note += f"- Patient expressed: \"{stmt}\"\n"
    else:
        # Parse for common dental complaints if no clear patient statements
        complaint_keywords = ['pain', 'hurt', 'broken', 'loose', 'missing', 'crown', 'tooth', 'bite']
        found_complaints = []
        for keyword in complaint_keywords:
            if keyword in transcript.lower():
                found_complaints.append(keyword)
        
        if found_complaints:
            soap_note += f"Patient consultation regarding: {', '.join(found_complaints[:3])}\n"
        else:
            soap_note += "Patient requested prosthodontic consultation.\n"
    
    # OBJECTIVE section  
    soap_note += "\nOBJECTIVE:\n"
    exam_keywords = ['exam', 'examination', 'looked', 'see', 'observe', 'x-ray', 'radiograph', 'photo']
    clinical_findings = []
    
    for stmt in doctor_statements:
        if any(keyword in stmt.lower() for keyword in exam_keywords):
            clinical_findings.append(stmt)
    
    if clinical_findings:
        soap_note += "Clinical examination revealed:\n"
        for finding in clinical_findings[:3]:
            soap_note += f"- {finding}\n"
    else:
        soap_note += "Clinical examination completed.\nDiagnostic records reviewed.\n"
    
    # ASSESSMENT section
    soap_note += "\nASSESSMENT:\n"
    assessment_keywords = ['diagnosis', 'problem', 'issue', 'condition', 'recommend', 'need']
    assessments = []
    
    for stmt in doctor_statements:
        if any(keyword in stmt.lower() for keyword in assessment_keywords):
            assessments.append(stmt)
    
    if assessments:
        soap_note += "Clinical assessment:\n"
        for assessment in assessments[:2]:
            soap_note += f"- {assessment}\n"
    else:
        soap_note += "Prosthodontic evaluation completed.\nTreatment planning indicated.\n"
    
    # PLAN section
    soap_note += "\nPLAN:\n"
    plan_keywords = ['treatment', 'plan', 'recommend', 'suggest', 'next', 'follow', 'schedule', 'return']
    plans = []
    
    for stmt in doctor_statements:
        if any(keyword in stmt.lower() for keyword in plan_keywords):
            plans.append(stmt)
    
    if plans:
        soap_note += "Treatment recommendations:\n"
        for plan in plans[:3]:
            soap_note += f"- {plan}\n"
    else:
        soap_note += "Treatment options reviewed with patient.\nFollow-up appointment recommended.\n"
    
    # Add note about AI processing
    soap_note += f"\n--- \nNote: This SOAP note was generated using AI processing of the clinical consultation transcript.\nFull conversation transcript available upon request.\n"
    
    return soap_note

def generate_post_visit_email(soap_note: str, patient_name: str, provider_name: str, appointment_date: str = None, transcript: str = None):
    """Generate a patient-friendly post-visit summary email using AI with knowledge base integration"""
    try:
        # Get relevant knowledge from AI memory for patient education
        knowledge_base = ""
        try:
            from database import get_all_knowledge_articles
            articles = get_all_knowledge_articles()
            if articles:
                knowledge_base = "\n🧠 AI MEMORY KNOWLEDGE BASE - USE FOR ACCURATE PATIENT EDUCATION:\n"
                for article in articles:
                    knowledge_base += f"\n📚 {article.get('title', 'Knowledge Item')} ({article.get('category', 'General')}):\n"
                    knowledge_base += f"{article.get('content', '')}\n"
                knowledge_base += "\n🚨 CRITICAL: Apply this knowledge for accurate patient information! 🚨\n"
        except Exception as e:
            logging.error(f"Error retrieving knowledge base for email: {e}")
            knowledge_base = ""
        
        # Create enhanced prompt for email generation
        current_date = format_for_email_timestamp() if not appointment_date else appointment_date
        
        prompt = f"""Create a professional, warm, and patient-friendly post-visit summary email based on the following information from a dental appointment.

{knowledge_base}

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
11. ✅ MUST use AI Memory knowledge to provide accurate information about procedures, treatments, and care instructions

CRITICAL REQUIREMENTS: 
- Use actual details from the SOAP note and transcript provided
- Convert medical terms to patient-friendly language using knowledge base
- Be specific about findings and recommendations based on stored protocols
- Make it personal and caring, not generic
- Apply ALL relevant knowledge from AI Memory for accurate patient education
- Follow established protocols and procedures from the knowledge base

Generate the email with Subject: and Body: clearly marked:"""

        # Call LLM API
        llm_config = get_current_llm_config()
        response = requests.post(
            f"{llm_config['host']}/api/generate",
            json={
                "model": llm_config["model"],
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
    session_id = get_session_id_with_timezone()
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
                        requested_template = message.get("template", "default")
                        
                        # Convert template display name to file ID if needed
                        template_name = convert_template_name_to_id(requested_template)
                        
                        logging.info(f"🔔 Session Info Received:")
                        logging.info(f"   Doctor: {doctor_name}")
                        logging.info(f"   Requested Template: {requested_template}")
                        logging.info(f"   Mapped Template ID: {template_name}")
                        logging.info(f"   Full message: {message}")
                        
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
        llm_config = get_current_llm_config()
        response = requests.post(
            f"{llm_config['host']}/api/generate",
            json={"model": llm_config["model"], "prompt": prompt, "stream": False},
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
        llm_config = get_current_llm_config()
        analysis_response = requests.post(
            f"{llm_config['host']}/api/generate",
            json={"model": llm_config["model"], "prompt": analysis_prompt, "stream": False},
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
            llm_config = get_current_llm_config()
            response = requests.post(
                f"{llm_config['host']}/api/generate",
                json={"model": llm_config["model"], "prompt": question_prompt, "stream": False},
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
            llm_config = get_current_llm_config()
            response = requests.post(
                f"{llm_config['host']}/api/generate",
                json={"model": llm_config["model"], "prompt": modification_prompt, "stream": False},
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
        "timestamp": now_in_system_timezone().isoformat()
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
        
        # Return in consistent format
        return {
            "status": "success",
            "email_content": email_result.get("body", ""),
            "subject": email_result.get("subject", ""),
            "message": "Email generated successfully"
        }
    except Exception as e:
        logging.error(f"Email generation error: {e}")
        return {
            "status": "error",
            "message": f"Failed to generate email: {str(e)}",
            "email_content": "",
            "subject": ""
        }

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

@app.get("/api/knowledge-articles/{article_id}")
async def get_knowledge_article_endpoint(article_id: str):
    """Get a single knowledge article by ID"""
    try:
        from database import get_all_knowledge_articles
        articles = get_all_knowledge_articles()
        article = next((a for a in articles if a['id'] == article_id), None)
        if article:
            return article
        else:
            raise HTTPException(status_code=404, detail="Article not found")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching knowledge article: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch knowledge article")

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
        
        # Enhanced training prompt with comprehensive knowledge integration
        training_prompt = f"""You are an AI assistant for a dental prosthodontics practice. You MUST follow stored knowledge and previous training exactly.

🧠 AI MEMORY KNOWLEDGE BASE - APPLY THIS KNOWLEDGE ALWAYS:
{knowledge_context}

🚨 CRITICAL INSTRUCTIONS:
- You MUST apply all knowledge from the AI Memory when responding
- When writing SOAP notes, you MUST follow template instructions precisely
- When creating emails, you MUST use stored protocols and procedures
- You MUST incorporate practice-specific knowledge and preferences
- Never give generic responses - always use the stored knowledge base

User Training Message: {request.message}

📋 RESPONSE REQUIREMENTS:
1. ✅ Apply relevant knowledge from AI Memory above
2. ✅ If this is feedback/training: Acknowledge and explain how you'll follow it
3. ✅ If this is a question: Answer using stored knowledge base
4. ✅ Focus on dental prosthodontics knowledge and SOAP documentation
5. ✅ Incorporate patient care protocols from memory
6. ✅ Reference treatment planning procedures from knowledge base
7. ✅ Use post-operative instructions from stored protocols

🎯 Key Focus Areas (use knowledge base for all):
- Dental prosthodontics procedures and protocols
- SOAP note documentation standards and templates
- Patient care best practices and communication
- Treatment planning workflows and decision trees
- Post-operative care instructions and follow-up protocols

Respond professionally while strictly following stored knowledge and training:"""

        # Send to LLM
        try:
            llm_config = get_current_llm_config()
            response = requests.post(
                f"{llm_config['host']}/api/generate",
                json={
                    "model": llm_config["model"],
                    "prompt": training_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=120  # Increased timeout for model initialization
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

@app.post("/api/knowledge/auto-learn")
async def auto_learn_from_interaction(data: dict):
    """Automatically learn and store knowledge from successful interactions"""
    try:
        interaction_type = data.get("type")  # "soap_generation", "email_generation", "training_feedback"
        content = data.get("content", "")
        feedback = data.get("feedback", "")
        success_rating = data.get("rating", 0)
        
        # Only store knowledge from highly rated interactions
        if success_rating >= 4:  # 4 or 5 star rating
            from database import create_knowledge_article
            
            # Generate knowledge article based on interaction type
            if interaction_type == "soap_generation":
                title = f"SOAP Note Best Practice - {datetime.now().strftime('%Y-%m-%d')}"
                category = "SOAP Documentation"
                knowledge_content = f"""Successful SOAP Note Pattern:

User Feedback: {feedback}
Rating: {success_rating}/5

Best Practice Learned:
{content}

This pattern should be followed for future SOAP note generation to maintain quality and consistency."""
                
            elif interaction_type == "email_generation":
                title = f"Post-Visit Email Best Practice - {datetime.now().strftime('%Y-%m-%d')}"
                category = "Patient Communication"
                knowledge_content = f"""Successful Email Pattern:

User Feedback: {feedback}
Rating: {success_rating}/5

Communication Best Practice:
{content}

This communication style should be used for future patient emails to maintain professionalism and clarity."""
                
            elif interaction_type == "training_feedback":
                title = f"Training Insight - {datetime.now().strftime('%Y-%m-%d')}"
                category = "AI Training"
                knowledge_content = f"""Important Training Feedback:

User Guidance: {content}
Feedback: {feedback}
Importance: {success_rating}/5

Key Learning:
The AI should incorporate this guidance in all future responses to maintain consistency with practice preferences."""
                
            else:
                return {"status": "Unknown interaction type"}
            
            # Store the knowledge
            result = create_knowledge_article(title, knowledge_content, category)
            if result:
                return {"status": "Knowledge learned and stored successfully", "article_id": result.get("id")}
            else:
                return {"status": "Failed to store knowledge"}
        else:
            return {"status": "Rating too low for knowledge storage"}
            
    except Exception as e:
        logging.error(f"Auto-learning error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process auto-learning")

# ====== LLM MODEL MANAGEMENT ENDPOINTS ======

@app.get("/api/llm/config")
async def get_llm_config():
    """Get current LLM configuration"""
    try:
        # Format current config as an object matching the frontend expectations
        current_llm_config = get_current_llm_config()
        formatted_config = None
        
        # Find the current model configuration
        formatted_config = None
        for model_key, config in LLM_CONFIGS.items():
            if config["host"] == current_llm_config["host"] and config["model"] == current_llm_config["model"]:
                formatted_config = {
                    "key": model_key,
                    "name": config["name"],
                    "model": config["model"],
                    "host": config["host"]
                }
                break
        
        return {"success": True, "config": formatted_config}
    except Exception as e:
        logging.error(f"Error getting LLM config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LLM configuration")

@app.post("/api/llm/config")
async def set_llm_config(request: dict):
    """Set current LLM configuration"""
    try:
        model_name = request.get("model", "llama")
        if model_name not in LLM_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        
        # Save the configuration choice to a file
        config_path = os.path.join(os.path.dirname(__file__), "llm_config.json")
        with open(config_path, "w") as f:
            json.dump({"current_model": model_name}, f)
        
        # Update global variables
        set_llm_model(model_name)
        
        # Format config as an object matching the frontend expectations
        config_data = LLM_CONFIGS[model_name]
        formatted_config = {
            "key": model_name,
            "name": config_data["name"],
            "model": config_data["model"],
            "host": config_data["host"]
        }
        
        return {"success": True, "config": formatted_config, "message": f"LLM switched to {config_data['name']}"}
    except Exception as e:
        logging.error(f"Error setting LLM config: {e}")
        raise HTTPException(status_code=500, detail="Failed to set LLM configuration")

@app.get("/api/llm/models")
async def get_available_models():
    """Get list of available LLM models"""
    try:
        models = []
        for model_key, config in LLM_CONFIGS.items():
            # Test connectivity to each model
            try:
                response = requests.get(f"{config['host']}/api/tags", timeout=5)
                available = response.status_code == 200
            except:
                available = False
                
            models.append({
                "key": model_key,
                "name": config["name"],
                "model": config["model"],
                "host": config["host"],
                "available": available
            })
        
        # Format current config as an object matching the frontend expectations
        current_llm_config = get_current_llm_config()
        current_config = None
        
        # Find the current model configuration
        for model_key, config in LLM_CONFIGS.items():
            if config["host"] == current_llm_config["host"] and config["model"] == current_llm_config["model"]:
                current_config = {
                    "key": model_key,
                    "name": config["name"],
                    "model": config["model"],
                    "host": config["host"]
                }
                break
        
        return {
            "success": True,
            "models": models,
            "current": current_config
        }
    except Exception as e:
        logging.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available models")

@app.post("/api/llm/test")
async def test_llm_connection(request: dict):
    """Test connection to a specific LLM model"""
    try:
        model_name = request.get("model", "llama")
        if model_name not in LLM_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        
        config = LLM_CONFIGS[model_name]
        
        # Test basic connectivity
        response = requests.get(f"{config['host']}/api/tags", timeout=10)
        if response.status_code != 200:
            return {"success": False, "error": "Cannot connect to LLM service"}
        
        # Test model availability
        tags_data = response.json()
        available_models = [model["name"] for model in tags_data.get("models", [])]
        
        if config["model"] not in available_models:
            return {
                "success": False, 
                "error": f"Model {config['model']} not found. Available models: {', '.join(available_models)}"
            }
        
        # Test generation
        test_response = requests.post(
            f"{config['host']}/api/generate",
            json={
                "model": config["model"],
                "prompt": "Test connection. Respond with 'OK'.",
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=15
        )
        
        if test_response.status_code == 200:
            result = test_response.json().get("response", "").strip()
            return {
                "success": True,
                "message": f"Successfully connected to {config['name']}",
                "response": result
            }
        else:
            return {"success": False, "error": "Model failed to generate response"}
            
    except Exception as e:
        logging.error(f"Error testing LLM connection: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/llm/status")
async def get_llm_status():
    """Get status of all available LLM models"""
    try:
        status = {}
        for model_key, config in LLM_CONFIGS.items():
            try:
                response = requests.get(f"{config['host']}/api/tags", timeout=5)
                status[model_key] = response.status_code == 200
            except:
                status[model_key] = False
        
        return status
    except Exception as e:
        logging.error(f"Error getting LLM status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LLM status")

@app.post("/api/llm/switch")
async def switch_llm_model(request: dict):
    """Switch to a different LLM model"""
    try:
        llm_type = request.get("llm_type")
        if not llm_type:
            raise HTTPException(status_code=400, detail="llm_type is required")
        
        if llm_type not in LLM_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown LLM type: {llm_type}")
        
        # Save the configuration choice to a file
        config_path = os.path.join(os.path.dirname(__file__), "llm_config.json")
        with open(config_path, "w") as f:
            json.dump({"current_model": llm_type}, f)
        
        # Update global variables
        set_llm_model(llm_type)
        
        return {"success": True, "message": f"Switched to {LLM_CONFIGS[llm_type]['name']}"}
    except Exception as e:
        logging.error(f"Error switching LLM: {e}")
        raise HTTPException(status_code=500, detail="Failed to switch LLM model")

# ============================================
# System Configuration API Endpoints
# ============================================

class SystemConfigRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

@app.get("/api/system-config")
async def get_all_system_configs():
    """Get all system configuration settings"""
    try:
        from database import get_all_system_configs
        configs = get_all_system_configs()
        return {"success": True, "configs": configs}
    except Exception as e:
        logging.error(f"Error getting system configs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system configurations")

@app.get("/api/system-config/{key}")
async def get_system_config_by_key(key: str):
    """Get a specific system configuration value"""
    try:
        from database import get_system_config
        value = get_system_config(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")
        return {"success": True, "key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting system config {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system configuration")

@app.post("/api/system-config")
async def set_system_config(request: SystemConfigRequest):
    """Set a system configuration value"""
    try:
        from database import set_system_config
        success = set_system_config(request.key, request.value, request.description)
        if success:
            return {"success": True, "message": f"Configuration '{request.key}' updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error setting system config: {e}")
        raise HTTPException(status_code=500, detail="Failed to set system configuration")

@app.get("/api/timezones")
async def get_available_timezones_api():
    """Get list of available timezones for configuration"""
    try:
        timezones = get_available_timezones()
        return {"success": True, "timezones": timezones}
    except Exception as e:
        logging.error(f"Error getting timezones: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available timezones")

@app.post("/api/timezone")
async def set_system_timezone(request: dict):
    """Set the system timezone"""
    try:
        timezone_name = request.get("timezone")
        if not timezone_name:
            raise HTTPException(status_code=400, detail="timezone is required")
        
        if not validate_timezone(timezone_name):
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone_name}")
        
        from database import set_system_config
        success = set_system_config("timezone", timezone_name, f"System timezone set to {timezone_name}")
        
        if success:
            return {"success": True, "message": f"Timezone set to {timezone_name}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update timezone")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error setting timezone: {e}")
        raise HTTPException(status_code=500, detail="Failed to set timezone")

@app.get("/api/timezone/current")
async def get_current_timezone():
    """Get current system timezone and formatted time"""
    try:
        from timezone_utils import get_system_timezone
        from database import get_system_config
        
        tz_name = get_system_config("timezone", "America/Denver")
        system_tz = get_system_timezone()
        current_time = now_in_system_timezone()
        
        return {
            "success": True,
            "timezone": tz_name,
            "current_time": format_datetime_for_display(current_time),
            "formatted_display": format_for_soap_note(current_time)
        }
    except Exception as e:
        logging.error(f"Error getting current timezone: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current timezone")

# Initialize default configurations on startup - DISABLED FOR NOW
# try:
#     from database import initialize_default_configs
#     initialize_default_configs()
# except Exception as e:
#     logging.warning(f"Could not initialize default configurations: {e}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Boise Prosthodontics AI Scribe...")
    print(f"Whisper: {'Enabled' if WHISPER_AVAILABLE else 'Mock Mode'}")
    print(f"Diarization: {'Enabled' if DIARIZATION_AVAILABLE else 'Single Speaker Mode'}")
    print(f"Ollama: {OLLAMA_HOST}")
    uvicorn.run(app, host="0.0.0.0", port=3051)