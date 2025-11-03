"""
Pytest configuration and fixtures for the AI Scribe test suite.
"""
import pytest
import os
import tempfile
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Import your application modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base, SessionLocal, get_db
from main import app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database for each test."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    database_url = f"sqlite:///{temp_db.name}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal()
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    os.unlink(temp_db.name)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def mock_provider_data():
    """Sample provider data for testing."""
    return {
        "id": 1,
        "name": "Dr. Test Provider",
        "specialty": "Prosthodontics",
        "credentials": "DDS, MS",
        "email": "test@example.com",
        "phone": "555-1234",
        "tenant_id": 1
    }


@pytest.fixture
def mock_session_data():
    """Sample session data for testing."""
    return {
        "session_id": "test-session-123",
        "doctor": "Dr. Test Provider",
        "provider_id": 1,
        "timestamp": datetime.utcnow().isoformat(),
        "transcript": "Patient presents with crown replacement on tooth #14. Discussion of treatment options including zirconia vs. PFM crown.",
        "soap_note": "S: Patient reports discomfort with existing crown.\nO: Crown #14 shows marginal defect.\nA: Defective crown #14.\nP: Replace crown with zirconia restoration.",
        "template_used": "treatment_consultation",
        "audio_file_path": "/test/audio/session-123.wav",
        "tenant_id": 1
    }


@pytest.fixture
def mock_tenant_data():
    """Sample tenant configuration data."""
    return {
        "tenant_id": 1,
        "practice_name": "Test Dental Practice",
        "config_path": "/test/config/tenant-1.json",
        "subscription_tier": "professional",
        "is_active": True
    }


@pytest.fixture
def mock_tenant_config():
    """Sample tenant configuration object."""
    return {
        "practice_name": "Test Dental Practice",
        "logo_url": "https://example.com/logo.png",
        "primary_color": "#1E40AF",
        "secondary_color": "#3B82F6",
        "features_enabled": {
            "ambient_scribe": True,
            "dentrix_integration": True,
            "voice_profiles": True,
            "openai_option": True,
            "email_system": True,
            "soap_templates": True
        },
        "dentrix_bridge_url": "http://localhost:3051",
        "whisper_model": "base"
    }


@pytest.fixture
def mock_voice_profile():
    """Mock voice profile data."""
    return {
        "provider_name": "Dr. Test Provider",
        "profile_path": "/test/profiles/dr-test-provider/profile.pkl",
        "sample_count": 5,
        "created_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for transcription."""
    mock = MagicMock()
    mock.transcribe.return_value = {
        "text": "This is a test transcription.",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "This is a test"},
            {"start": 2.5, "end": 4.0, "text": "transcription."}
        ]
    }
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for SOAP note generation."""
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="S: Test subjective\nO: Test objective\nA: Test assessment\nP: Test plan"
                )
            )
        ]
    )
    return mock


@pytest.fixture
def mock_dentrix_client():
    """Mock Dentrix client."""
    mock = MagicMock()
    mock.check_health.return_value = {"status": "healthy", "version": "1.0.0"}
    mock.send_note.return_value = {"success": True, "patient_id": "12345"}
    return mock


@pytest.fixture
def mock_encryption_manager():
    """Mock encryption manager."""
    mock = MagicMock()
    mock.encrypt.return_value = b"encrypted_data"
    mock.decrypt.return_value = "decrypted_data"
    return mock


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    # Write some dummy WAV header and data
    temp_file.write(b'RIFF' + b'\x00' * 100)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def temp_export_dir():
    """Create a temporary directory for export testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_csv_file():
    """Create a mock CSV file for import testing."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
    temp_file.write("name,specialty,credentials,email\n")
    temp_file.write("Dr. John Doe,Prosthodontics,DDS,john@example.com\n")
    temp_file.write("Dr. Jane Smith,Orthodontics,DDS MS,jane@example.com\n")
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def mock_json_template():
    """Create a mock JSON template file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    template_data = {
        "name": "Test Template",
        "sections": {
            "subjective": ["chief_complaint", "history"],
            "objective": ["examination", "findings"],
            "assessment": ["diagnosis"],
            "plan": ["treatment", "follow_up"]
        }
    }
    json.dump(template_data, temp_file)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Fixture to measure execution time."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
