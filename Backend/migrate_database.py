from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

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

def migrate_database():
    """Migrate existing database to new schema"""
    engine = create_engine('sqlite:///sessions.db')
    
    # Get inspector to check current schema
    inspector = inspect(engine)
    
    print("Checking database schema...")
    
    # Check if tables exist
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")
    
    if 'sessions' in existing_tables:
        # Check current columns
        current_columns = [col['name'] for col in inspector.get_columns('sessions')]
        print(f"Current session columns: {current_columns}")
        
        # New columns we need
        required_columns = [
            'patient_name',
            'patient_email_encrypted', 
            'post_visit_email',
            'email_sent',
            'email_sent_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in current_columns]
        print(f"Missing columns: {missing_columns}")
        
        if missing_columns:
            print("Adding missing columns...")
            with engine.connect() as conn:
                for column in missing_columns:
                    if column == 'patient_name':
                        conn.execute(text(f'ALTER TABLE sessions ADD COLUMN {column} TEXT'))
                    elif column == 'patient_email_encrypted':
                        conn.execute(text(f'ALTER TABLE sessions ADD COLUMN {column} TEXT'))
                    elif column == 'post_visit_email':
                        conn.execute(text(f'ALTER TABLE sessions ADD COLUMN {column} TEXT'))
                    elif column == 'email_sent':
                        conn.execute(text(f'ALTER TABLE sessions ADD COLUMN {column} BOOLEAN DEFAULT 0'))
                    elif column == 'email_sent_at':
                        conn.execute(text(f'ALTER TABLE sessions ADD COLUMN {column} DATETIME'))
                conn.commit()
            print("✅ Database migration completed!")
        else:
            print("✅ Database schema is up to date!")
    else:
        print("Creating new database schema...")
        Base.metadata.create_all(engine)
        print("✅ New database created!")

if __name__ == "__main__":
    migrate_database()