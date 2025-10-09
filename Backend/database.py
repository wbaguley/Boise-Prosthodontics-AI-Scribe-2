from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

Base = declarative_base()

class Provider(Base):
    """Provider/Doctor table"""
    __tablename__ = 'providers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    specialty = Column(String, nullable=True)
    credentials = Column(String, nullable=True)
    email = Column(String, nullable=True)
    has_voice_profile = Column(Boolean, default=False)
    voice_profile_path = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Session(Base):
    """Recording session table"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True)
    provider_id = Column(Integer, nullable=True)  # Foreign key to Provider
    doctor_name = Column(String)
    patient_id = Column(String, nullable=True)
    patient_name = Column(String, nullable=True)
    patient_email_encrypted = Column(Text, nullable=True)  # Encrypted patient email
    timestamp = Column(DateTime, default=datetime.utcnow)
    transcript = Column(Text)
    soap_note = Column(Text)
    post_visit_email = Column(Text, nullable=True)  # Generated email content
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    audio_path = Column(String, nullable=True)
    template_used = Column(String, nullable=True)
    session_metadata = Column(Text, nullable=True)

# Create database
engine = create_engine('sqlite:///sessions.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# ============================================
# Provider CRUD Operations
# ============================================

def create_provider(name, specialty=None, credentials=None, email=None):
    """Create a new provider or reactivate existing inactive one"""
    db = SessionLocal()
    try:
        # Check if provider already exists (including inactive ones)
        existing_provider = db.query(Provider).filter(Provider.name == name).first()
        
        if existing_provider:
            if not existing_provider.is_active:
                # Reactivate the existing provider with updated info
                existing_provider.is_active = True
                existing_provider.specialty = specialty
                existing_provider.credentials = credentials  
                existing_provider.email = email
                existing_provider.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing_provider)
                return {
                    'id': existing_provider.id,
                    'name': existing_provider.name,
                    'specialty': existing_provider.specialty,
                    'credentials': existing_provider.credentials,
                    'email': existing_provider.email,
                    'has_voice_profile': existing_provider.has_voice_profile,
                    'is_active': existing_provider.is_active
                }
            else:
                # Provider is already active
                print(f"Provider {name} already exists and is active")
                return None
        
        # Create new provider
        provider = Provider(
            name=name,
            specialty=specialty,
            credentials=credentials,
            email=email
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return {
            'id': provider.id,
            'name': provider.name,
            'specialty': provider.specialty,
            'credentials': provider.credentials,
            'email': provider.email,
            'has_voice_profile': provider.has_voice_profile,
            'is_active': provider.is_active
        }
    except Exception as e:
        print(f"Error creating provider: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_all_providers(active_only=True):
    """Get all providers"""
    db = SessionLocal()
    try:
        query = db.query(Provider)
        if active_only:
            query = query.filter(Provider.is_active == True)
        
        providers = query.order_by(Provider.name).all()
        return [
            {
                'id': p.id,
                'name': p.name,
                'specialty': p.specialty,
                'credentials': p.credentials,
                'email': p.email,
                'has_voice_profile': p.has_voice_profile,
                'is_active': p.is_active
            }
            for p in providers
        ]
    except Exception as e:
        print(f"Error fetching providers: {e}")
        return []
    finally:
        db.close()

def get_provider_by_id(provider_id):
    """Get provider by ID"""
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if provider:
            return {
                'id': provider.id,
                'name': provider.name,
                'specialty': provider.specialty,
                'credentials': provider.credentials,
                'email': provider.email,
                'has_voice_profile': provider.has_voice_profile,
                'voice_profile_path': provider.voice_profile_path,
                'is_active': provider.is_active
            }
        return None
    finally:
        db.close()

def get_provider_by_name(name):
    """Get provider by name"""
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.name == name).first()
        if provider:
            return {
                'id': provider.id,
                'name': provider.name,
                'specialty': provider.specialty,
                'credentials': provider.credentials,
                'email': provider.email,
                'has_voice_profile': provider.has_voice_profile,
                'voice_profile_path': provider.voice_profile_path,
                'is_active': provider.is_active
            }
        return None
    finally:
        db.close()

def update_provider(provider_id, **kwargs):
    """Update provider details"""
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            return None
        
        for key, value in kwargs.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        
        provider.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(provider)
        
        return {
            'id': provider.id,
            'name': provider.name,
            'specialty': provider.specialty,
            'credentials': provider.credentials,
            'email': provider.email,
            'has_voice_profile': provider.has_voice_profile,
            'is_active': provider.is_active
        }
    except Exception as e:
        print(f"Error updating provider: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def delete_provider(provider_id):
    """Soft delete a provider (set is_active to False)"""
    db = SessionLocal()
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if provider:
            provider.is_active = False
            provider.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting provider: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_provider_voice_profile(provider_id, voice_profile_path):
    """Update provider's voice profile information"""
    return update_provider(
        provider_id,
        has_voice_profile=True,
        voice_profile_path=voice_profile_path
    )

# ============================================
# Session CRUD Operations
# ============================================

def save_session(session_id, doctor, transcript, soap_note, template=None, provider_id=None):
    """Save session to database"""
    db = SessionLocal()
    try:
        session = Session(
            session_id=session_id,
            provider_id=provider_id,
            doctor_name=doctor,
            transcript=transcript,
            soap_note=soap_note,
            template_used=template,
            timestamp=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_all_sessions():
    """Get all sessions for display"""
    db = SessionLocal()
    try:
        sessions = db.query(Session).order_by(Session.timestamp.desc()).all()
        return [
            {
                'session_id': s.session_id,
                'doctor': s.doctor_name,
                'provider_id': s.provider_id,
                'timestamp': s.timestamp.isoformat() if s.timestamp else '',
                'transcript': s.transcript[:100] + '...' if s.transcript and len(s.transcript) > 100 else s.transcript or '',
                'soap_note': s.soap_note[:100] + '...' if s.soap_note and len(s.soap_note) > 100 else s.soap_note or '',
                'template': s.template_used
            }
            for s in sessions
        ]
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        db.close()

def get_session_by_id(session_id):
    """Get full session details"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if session:
            return {
                'session_id': session.session_id,
                'doctor': session.doctor_name,
                'provider_id': session.provider_id,
                'timestamp': session.timestamp.isoformat() if session.timestamp else '',
                'transcript': session.transcript or '',
                'soap_note': session.soap_note or '',
                'template_used': session.template_used
            }
        return None
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        db.close()

def get_sessions_by_provider(provider_id):
    """Get all sessions for a specific provider"""
    db = SessionLocal()
    try:
        sessions = db.query(Session).filter(
            Session.provider_id == provider_id
        ).order_by(Session.timestamp.desc()).all()
        
        return [
            {
                'session_id': s.session_id,
                'doctor': s.doctor_name,
                'timestamp': s.timestamp.isoformat() if s.timestamp else '',
                'transcript': s.transcript[:100] + '...' if s.transcript else '',
                'soap_note': s.soap_note[:100] + '...' if s.soap_note else '',
                'template': s.template_used
            }
            for s in sessions
        ]
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        db.close()

def update_session_soap(session_id, soap_note):
    """Update the SOAP note for a specific session"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if session:
            session.soap_note = soap_note
            # Add updated timestamp if you have that field
            # session.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating session SOAP: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_session_template(session_id, template_used):
    """Update the template used for a specific session"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if session:
            session.template_used = template_used
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating session template: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_session_patient_info(session_id: str, patient_name: str, patient_email_encrypted: str, patient_id: str = None):
    """Update session with patient information"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            session.patient_name = patient_name
            session.patient_email_encrypted = patient_email_encrypted
            if patient_id:
                session.patient_id = patient_id
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating session patient info: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_session_email_content(session_id: str, email_content: str):
    """Update session with post-visit email content"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            session.post_visit_email = email_content
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error updating session email content: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def mark_email_sent(session_id: str):
    """Mark email as sent for a session"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            session.email_sent = True
            session.email_sent_at = datetime.utcnow()
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Error marking email as sent: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_session_email_status(session_id: str):
    """Get email status for a session"""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            return {
                "email_sent": session.email_sent or False,
                "email_sent_at": session.email_sent_at.isoformat() if session.email_sent_at else None,
                "has_email_content": bool(session.post_visit_email),
                "patient_name": session.patient_name,
                "patient_email_encrypted": session.patient_email_encrypted
            }
        return None
    except Exception as e:
        print(f"Error getting email status: {e}")
        return None
    finally:
        db.close()

# Knowledge Articles Management
def create_knowledge_article(title: str, content: str, category: str):
    """Create a new knowledge article"""
    db = SessionLocal()
    try:
        # Create simple dictionary entry for now (could be expanded to a proper table)
        article_data = {
            'id': str(uuid4()),
            'title': title,
            'content': content,
            'category': category,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # For now, we'll store in a simple JSON file
        articles_file = Path('knowledge_articles.json')
        articles = []
        if articles_file.exists():
            with open(articles_file, 'r') as f:
                articles = json.load(f)
        
        articles.append(article_data)
        
        with open(articles_file, 'w') as f:
            json.dump(articles, f, indent=2)
            
        return article_data
    except Exception as e:
        print(f"Error creating knowledge article: {e}")
        return None
    finally:
        db.close()

def get_all_knowledge_articles():
    """Get all knowledge articles"""
    try:
        articles_file = Path('knowledge_articles.json')
        if articles_file.exists():
            with open(articles_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error getting knowledge articles: {e}")
        return []

def delete_knowledge_article(article_id: str):
    """Delete a knowledge article"""
    try:
        articles_file = Path('knowledge_articles.json')
        if articles_file.exists():
            with open(articles_file, 'r') as f:
                articles = json.load(f)
            
            articles = [a for a in articles if a['id'] != article_id]
            
            with open(articles_file, 'w') as f:
                json.dump(articles, f, indent=2)
            
            return True
        return False
    except Exception as e:
        print(f"Error deleting knowledge article: {e}")
        return False

def update_knowledge_article(article_id: str, title: str, content: str, category: str):
    """Update a knowledge article"""
    try:
        articles_file = Path('knowledge_articles.json')
        if articles_file.exists():
            with open(articles_file, 'r') as f:
                articles = json.load(f)
            
            # Find and update the article
            for article in articles:
                if article['id'] == article_id:
                    article['title'] = title
                    article['content'] = content
                    article['category'] = category
                    article['updated_at'] = datetime.utcnow().isoformat()
                    
                    with open(articles_file, 'w') as f:
                        json.dump(articles, f, indent=2)
                    
                    return article
            
            return None  # Article not found
        return None
    except Exception as e:
        print(f"Error updating knowledge article: {e}")
        return None

def get_knowledge_articles_by_category(category: str):
    """Get knowledge articles by category"""
    try:
        articles = get_all_knowledge_articles()
        return [a for a in articles if a['category'] == category]
    except Exception as e:
        print(f"Error getting articles by category: {e}")
        return []

def delete_session_by_id(session_id: str):
    """Delete a session by its ID"""
    db = SessionLocal()
    try:
        print(f"Looking for session with ID: {session_id}")
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            print(f"Found session, deleting: {session.session_id}")
            db.delete(session)
            db.commit()
            print(f"Session {session_id} deleted successfully")
            return True
        else:
            print(f"Session {session_id} not found in database")
            return False
    except Exception as e:
        print(f"Error deleting session {session_id}: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.rollback()
        return False
    finally:
        db.close()