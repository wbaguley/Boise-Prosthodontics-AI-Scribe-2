"""
Test suite for Export Service functionality.
Tests PDF, DOCX, CSV, and ZIP export features.
"""
import pytest
import os
import io
from datetime import datetime, timedelta
from export_service import ExportService


class TestExportService:
    """Test cases for ExportService class."""
    
    @pytest.fixture
    def export_service(self):
        """Create ExportService instance."""
        return ExportService()
    
    # ========================================================================
    # PDF Export Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_export_session_to_pdf_success(self, export_service, mock_session_data):
        """Test successful PDF export of a session."""
        # Act
        pdf_bytes = export_service.export_session_to_pdf(mock_session_data)
        
        # Assert
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')  # PDF magic bytes
    
    @pytest.mark.unit
    def test_export_session_to_pdf_with_missing_data(self, export_service):
        """Test PDF export with minimal session data."""
        # Arrange
        minimal_session = {
            "session_id": "test-123",
            "doctor": "Dr. Test",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Act
        pdf_bytes = export_service.export_session_to_pdf(minimal_session)
        
        # Assert
        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    @pytest.mark.unit
    def test_export_session_to_pdf_with_invalid_input(self, export_service):
        """Test PDF export with invalid input data."""
        # Arrange
        invalid_session = None
        
        # Act & Assert
        with pytest.raises(Exception):
            export_service.export_session_to_pdf(invalid_session)
    
    @pytest.mark.performance
    def test_export_session_to_pdf_performance(self, export_service, mock_session_data, performance_timer):
        """Test PDF export completes within 2 seconds."""
        # Act
        performance_timer.start()
        pdf_bytes = export_service.export_session_to_pdf(mock_session_data)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"PDF export took {performance_timer.elapsed}s, expected < 2s"
        assert pdf_bytes is not None
    
    # ========================================================================
    # DOCX Export Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_export_session_to_docx_success(self, export_service, mock_session_data):
        """Test successful DOCX export of a session."""
        # Act
        docx_bytes = export_service.export_session_to_docx(mock_session_data)
        
        # Assert
        assert docx_bytes is not None
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0
        # DOCX files are ZIP archives
        assert docx_bytes.startswith(b'PK')
    
    @pytest.mark.unit
    def test_export_session_to_docx_with_missing_data(self, export_service):
        """Test DOCX export with minimal data."""
        # Arrange
        minimal_session = {
            "session_id": "test-123",
            "doctor": "Dr. Test",
            "timestamp": datetime.utcnow().isoformat(),
            "soap_note": None,
            "transcript": None
        }
        
        # Act
        docx_bytes = export_service.export_session_to_docx(minimal_session)
        
        # Assert
        assert docx_bytes is not None
        assert len(docx_bytes) > 0
    
    @pytest.mark.unit
    def test_export_session_to_docx_with_invalid_input(self, export_service):
        """Test DOCX export error handling."""
        # Act & Assert
        with pytest.raises(Exception):
            export_service.export_session_to_docx({})
    
    @pytest.mark.performance
    def test_export_session_to_docx_performance(self, export_service, mock_session_data, performance_timer):
        """Test DOCX export completes within 2 seconds."""
        # Act
        performance_timer.start()
        docx_bytes = export_service.export_session_to_docx(mock_session_data)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"DOCX export took {performance_timer.elapsed}s, expected < 2s"
        assert docx_bytes is not None
    
    # ========================================================================
    # CSV Export Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_export_sessions_to_csv_success(self, export_service, mock_session_data):
        """Test successful CSV export of multiple sessions."""
        # Arrange
        sessions = [
            mock_session_data,
            {**mock_session_data, "session_id": "test-session-456"},
            {**mock_session_data, "session_id": "test-session-789"}
        ]
        
        # Act
        csv_string = export_service.export_sessions_to_csv(sessions)
        
        # Assert
        assert csv_string is not None
        assert isinstance(csv_string, str)
        assert "session_id" in csv_string
        assert "test-session-123" in csv_string
        assert "test-session-456" in csv_string
        lines = csv_string.split('\n')
        assert len(lines) >= 4  # Header + 3 sessions + empty line
    
    @pytest.mark.unit
    def test_export_sessions_to_csv_with_filters(self, export_service, mock_session_data):
        """Test CSV export with provider filter."""
        # Arrange
        sessions = [
            {**mock_session_data, "provider_id": 1, "doctor": "Dr. Smith"},
            {**mock_session_data, "session_id": "test-456", "provider_id": 2, "doctor": "Dr. Jones"},
            {**mock_session_data, "session_id": "test-789", "provider_id": 1, "doctor": "Dr. Smith"}
        ]
        
        # Act - filter by provider_id = 1
        filtered_sessions = [s for s in sessions if s["provider_id"] == 1]
        csv_string = export_service.export_sessions_to_csv(filtered_sessions)
        
        # Assert
        assert "Dr. Smith" in csv_string
        assert "Dr. Jones" not in csv_string
        lines = csv_string.strip().split('\n')
        assert len(lines) == 3  # Header + 2 sessions
    
    @pytest.mark.unit
    def test_export_sessions_to_csv_with_empty_list(self, export_service):
        """Test CSV export with empty session list."""
        # Act
        csv_string = export_service.export_sessions_to_csv([])
        
        # Assert
        assert csv_string is not None
        assert "session_id" in csv_string  # Header should still be present
    
    @pytest.mark.performance
    def test_export_sessions_to_csv_performance(self, export_service, mock_session_data, performance_timer):
        """Test CSV export of 100 sessions completes within 2 seconds."""
        # Arrange - create 100 sessions
        sessions = [
            {**mock_session_data, "session_id": f"test-{i}"}
            for i in range(100)
        ]
        
        # Act
        performance_timer.start()
        csv_string = export_service.export_sessions_to_csv(sessions)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"CSV export took {performance_timer.elapsed}s, expected < 2s"
        assert csv_string is not None
        lines = csv_string.strip().split('\n')
        assert len(lines) == 101  # Header + 100 sessions
    
    # ========================================================================
    # Voice Profile Export Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_export_voice_profile_success(self, export_service, mock_voice_profile, temp_export_dir):
        """Test successful voice profile export as ZIP."""
        # Arrange - create mock profile files
        profile_dir = os.path.join(temp_export_dir, "dr-test-provider")
        os.makedirs(profile_dir, exist_ok=True)
        
        # Create mock profile.pkl
        profile_path = os.path.join(profile_dir, "profile.pkl")
        with open(profile_path, 'wb') as f:
            f.write(b'mock_profile_data')
        
        # Create mock metadata.json
        import json
        metadata_path = os.path.join(profile_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump({"provider": "Dr. Test Provider", "created": datetime.utcnow().isoformat()}, f)
        
        # Create mock audio samples
        samples_dir = os.path.join(profile_dir, "samples")
        os.makedirs(samples_dir, exist_ok=True)
        for i in range(3):
            sample_path = os.path.join(samples_dir, f"sample_{i}.wav")
            with open(sample_path, 'wb') as f:
                f.write(b'RIFF' + b'\x00' * 100)
        
        # Act
        zip_bytes = export_service.export_voice_profile(profile_dir)
        
        # Assert
        assert zip_bytes is not None
        assert isinstance(zip_bytes, bytes)
        assert len(zip_bytes) > 0
        assert zip_bytes.startswith(b'PK')  # ZIP magic bytes
    
    @pytest.mark.unit
    def test_export_voice_profile_with_missing_files(self, export_service, temp_export_dir):
        """Test voice profile export with missing files."""
        # Arrange - create directory but no files
        profile_dir = os.path.join(temp_export_dir, "empty-profile")
        os.makedirs(profile_dir, exist_ok=True)
        
        # Act
        zip_bytes = export_service.export_voice_profile(profile_dir)
        
        # Assert - should still create a zip, even if empty
        assert zip_bytes is not None
        assert isinstance(zip_bytes, bytes)
    
    @pytest.mark.unit
    def test_export_voice_profile_with_invalid_path(self, export_service):
        """Test voice profile export with non-existent path."""
        # Act & Assert
        with pytest.raises(Exception):
            export_service.export_voice_profile("/nonexistent/path")


class TestExportAPIEndpoints:
    """Test cases for export API endpoints."""
    
    @pytest.mark.integration
    def test_export_pdf_endpoint(self, client, test_db, mock_session_data):
        """Test /api/sessions/{session_id}/export/pdf endpoint."""
        # Arrange - create a session in database
        from database import Session, Provider
        provider = Provider(
            name=mock_session_data["doctor"],
            specialty="Prosthodontics",
            credentials="DDS"
        )
        test_db.add(provider)
        test_db.commit()
        
        session = Session(
            session_id=mock_session_data["session_id"],
            doctor=mock_session_data["doctor"],
            provider_id=provider.id,
            transcript=mock_session_data["transcript"],
            soap_note=mock_session_data["soap_note"],
            template_used=mock_session_data["template_used"]
        )
        test_db.add(session)
        test_db.commit()
        
        # Act
        response = client.get(f"/api/sessions/{mock_session_data['session_id']}/export/pdf")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content.startswith(b'%PDF')
    
    @pytest.mark.integration
    def test_export_docx_endpoint(self, client, test_db, mock_session_data):
        """Test /api/sessions/{session_id}/export/docx endpoint."""
        # Arrange
        from database import Session, Provider
        provider = Provider(name=mock_session_data["doctor"], specialty="Test")
        test_db.add(provider)
        test_db.commit()
        
        session = Session(
            session_id=mock_session_data["session_id"],
            doctor=mock_session_data["doctor"],
            provider_id=provider.id,
            transcript=mock_session_data["transcript"],
            soap_note=mock_session_data["soap_note"]
        )
        test_db.add(session)
        test_db.commit()
        
        # Act
        response = client.get(f"/api/sessions/{mock_session_data['session_id']}/export/docx")
        
        # Assert
        assert response.status_code == 200
        assert "application/vnd.openxmlformats" in response.headers["content-type"]
        assert len(response.content) > 0
    
    @pytest.mark.integration
    def test_export_csv_endpoint(self, client, test_db, mock_session_data):
        """Test /api/sessions/export/csv endpoint."""
        # Arrange - create multiple sessions
        from database import Session, Provider
        provider = Provider(name="Dr. Test", specialty="Test")
        test_db.add(provider)
        test_db.commit()
        
        for i in range(5):
            session = Session(
                session_id=f"test-{i}",
                doctor="Dr. Test",
                provider_id=provider.id,
                transcript=f"Transcript {i}",
                soap_note=f"SOAP {i}"
            )
            test_db.add(session)
        test_db.commit()
        
        # Act
        response = client.get("/api/sessions/export/csv")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert b"session_id" in response.content
        assert b"test-0" in response.content
    
    @pytest.mark.integration
    def test_export_pdf_not_found(self, client):
        """Test PDF export with non-existent session."""
        # Act
        response = client.get("/api/sessions/nonexistent-session/export/pdf")
        
        # Assert
        assert response.status_code == 404
