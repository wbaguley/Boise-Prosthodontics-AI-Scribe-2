"""
Test suite for Import Service functionality.
Tests ZIP, CSV, and JSON import features.
"""
import pytest
import os
import json
import zipfile
import tempfile
from import_service import ImportService


class TestImportService:
    """Test cases for ImportService class."""
    
    @pytest.fixture
    def import_service(self):
        """Create ImportService instance."""
        return ImportService()
    
    # ========================================================================
    # Voice Profile Import Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_import_voice_profile_success(self, import_service, temp_export_dir):
        """Test successful voice profile import from ZIP."""
        # Arrange - create a valid ZIP file
        zip_path = os.path.join(temp_export_dir, "profile.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # Add profile.pkl
            zf.writestr("profile.pkl", b"mock_profile_data")
            # Add metadata.json
            metadata = {"provider": "Dr. Test", "created": "2024-01-01T00:00:00"}
            zf.writestr("metadata.json", json.dumps(metadata))
            # Add sample audio files
            zf.writestr("samples/sample_0.wav", b"RIFF" + b"\x00" * 100)
            zf.writestr("samples/sample_1.wav", b"RIFF" + b"\x00" * 100)
        
        # Act
        result = import_service.import_voice_profile(zip_path, "dr-test-provider", temp_export_dir)
        
        # Assert
        assert result["success"] is True
        assert "profile_path" in result
        assert os.path.exists(result["profile_path"])
    
    @pytest.mark.unit
    def test_import_voice_profile_with_invalid_zip(self, import_service, temp_export_dir):
        """Test voice profile import with invalid ZIP file."""
        # Arrange - create an invalid file
        invalid_zip = os.path.join(temp_export_dir, "invalid.zip")
        with open(invalid_zip, 'w') as f:
            f.write("not a zip file")
        
        # Act & Assert
        with pytest.raises(Exception):
            import_service.import_voice_profile(invalid_zip, "test", temp_export_dir)
    
    @pytest.mark.unit
    def test_import_voice_profile_with_missing_profile_pkl(self, import_service, temp_export_dir):
        """Test voice profile import with missing profile.pkl."""
        # Arrange - create ZIP without profile.pkl
        zip_path = os.path.join(temp_export_dir, "incomplete.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("metadata.json", '{"test": "data"}')
        
        # Act
        result = import_service.import_voice_profile(zip_path, "test", temp_export_dir)
        
        # Assert
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.performance
    def test_import_voice_profile_performance(self, import_service, temp_export_dir, performance_timer):
        """Test voice profile import completes within 2 seconds."""
        # Arrange - create a realistic ZIP with multiple samples
        zip_path = os.path.join(temp_export_dir, "large_profile.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("profile.pkl", b"x" * 10000)  # 10KB profile
            zf.writestr("metadata.json", json.dumps({"test": "data"}))
            # Add 20 audio samples
            for i in range(20):
                zf.writestr(f"samples/sample_{i}.wav", b"RIFF" + b"\x00" * 1000)
        
        # Act
        performance_timer.start()
        result = import_service.import_voice_profile(zip_path, "test", temp_export_dir)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"Import took {performance_timer.elapsed}s, expected < 2s"
        assert result["success"] is True
    
    # ========================================================================
    # Provider CSV Import Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_import_providers_csv_success(self, import_service, mock_csv_file, test_db):
        """Test successful provider import from CSV."""
        # Act
        result = import_service.import_providers_csv(mock_csv_file, test_db)
        
        # Assert
        assert result["success"] is True
        assert result["created"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
        
        # Verify providers in database
        from database import Provider
        providers = test_db.query(Provider).all()
        assert len(providers) == 2
        assert providers[0].name == "Dr. John Doe"
        assert providers[1].name == "Dr. Jane Smith"
    
    @pytest.mark.unit
    def test_import_providers_csv_with_duplicates(self, import_service, temp_export_dir, test_db):
        """Test provider import with duplicate entries."""
        # Arrange - create CSV with duplicates
        csv_path = os.path.join(temp_export_dir, "duplicates.csv")
        with open(csv_path, 'w') as f:
            f.write("name,specialty,credentials,email\n")
            f.write("Dr. Test,Prostho,DDS,test@example.com\n")
            f.write("Dr. Test,Prostho,DDS,test@example.com\n")  # Duplicate
        
        # Act
        result = import_service.import_providers_csv(csv_path, test_db)
        
        # Assert
        assert result["created"] == 1  # Only first one created
        assert result["failed"] >= 1   # Duplicate failed
    
    @pytest.mark.unit
    def test_import_providers_csv_with_invalid_data(self, import_service, temp_export_dir, test_db):
        """Test provider import with missing required fields."""
        # Arrange - create CSV with missing fields
        csv_path = os.path.join(temp_export_dir, "invalid.csv")
        with open(csv_path, 'w') as f:
            f.write("name,specialty\n")
            f.write("Dr. Test,Prostho\n")  # Missing credentials and email
        
        # Act
        result = import_service.import_providers_csv(csv_path, test_db)
        
        # Assert
        # Should handle missing optional fields gracefully
        assert "created" in result
        assert "failed" in result
    
    @pytest.mark.unit
    def test_import_providers_csv_with_empty_file(self, import_service, temp_export_dir, test_db):
        """Test provider import with empty CSV."""
        # Arrange
        csv_path = os.path.join(temp_export_dir, "empty.csv")
        with open(csv_path, 'w') as f:
            f.write("name,specialty,credentials,email\n")  # Header only
        
        # Act
        result = import_service.import_providers_csv(csv_path, test_db)
        
        # Assert
        assert result["created"] == 0
        assert result["failed"] == 0
    
    @pytest.mark.performance
    def test_import_providers_csv_performance(self, import_service, temp_export_dir, test_db, performance_timer):
        """Test CSV import of 100 providers completes within 2 seconds."""
        # Arrange - create CSV with 100 providers
        csv_path = os.path.join(temp_export_dir, "large.csv")
        with open(csv_path, 'w') as f:
            f.write("name,specialty,credentials,email\n")
            for i in range(100):
                f.write(f"Dr. Test {i},Prosthodontics,DDS,test{i}@example.com\n")
        
        # Act
        performance_timer.start()
        result = import_service.import_providers_csv(csv_path, test_db)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"Import took {performance_timer.elapsed}s, expected < 2s"
        assert result["created"] == 100
    
    # ========================================================================
    # SOAP Template Import Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_import_soap_templates_success(self, import_service, mock_json_template, temp_export_dir):
        """Test successful SOAP template import from JSON."""
        # Act
        result = import_service.import_soap_templates(mock_json_template, temp_export_dir)
        
        # Assert
        assert result["success"] is True
        assert "template_path" in result
        assert os.path.exists(result["template_path"])
        
        # Verify template content
        with open(result["template_path"], 'r') as f:
            template = json.load(f)
        assert template["name"] == "Test Template"
        assert "sections" in template
    
    @pytest.mark.unit
    def test_import_soap_templates_with_invalid_json(self, import_service, temp_export_dir):
        """Test template import with invalid JSON."""
        # Arrange
        invalid_json = os.path.join(temp_export_dir, "invalid.json")
        with open(invalid_json, 'w') as f:
            f.write("{invalid json content")
        
        # Act & Assert
        with pytest.raises(Exception):
            import_service.import_soap_templates(invalid_json, temp_export_dir)
    
    @pytest.mark.unit
    def test_import_soap_templates_with_missing_fields(self, import_service, temp_export_dir):
        """Test template import with missing required fields."""
        # Arrange
        incomplete_json = os.path.join(temp_export_dir, "incomplete.json")
        with open(incomplete_json, 'w') as f:
            json.dump({"name": "Incomplete"}, f)  # Missing 'sections'
        
        # Act
        result = import_service.import_soap_templates(incomplete_json, temp_export_dir)
        
        # Assert
        # Should validate and reject incomplete templates
        assert result["success"] is False or "error" in result
    
    @pytest.mark.performance
    def test_import_soap_templates_performance(self, import_service, temp_export_dir, performance_timer):
        """Test template import completes within 2 seconds."""
        # Arrange - create a large template
        large_template = os.path.join(temp_export_dir, "large.json")
        template_data = {
            "name": "Large Template",
            "sections": {
                f"section_{i}": [f"field_{j}" for j in range(10)]
                for i in range(50)
            }
        }
        with open(large_template, 'w') as f:
            json.dump(template_data, f)
        
        # Act
        performance_timer.start()
        result = import_service.import_soap_templates(large_template, temp_export_dir)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"Import took {performance_timer.elapsed}s, expected < 2s"


class TestImportAPIEndpoints:
    """Test cases for import API endpoints."""
    
    @pytest.mark.integration
    def test_import_voice_profile_endpoint(self, client, temp_export_dir):
        """Test /api/voice-profiles/{provider_name}/import endpoint."""
        # Arrange - create a ZIP file
        zip_path = os.path.join(temp_export_dir, "profile.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("profile.pkl", b"test_data")
            zf.writestr("metadata.json", json.dumps({"test": "data"}))
        
        # Act
        with open(zip_path, 'rb') as f:
            response = client.post(
                "/api/voice-profiles/dr-test-provider/import",
                files={"file": ("profile.zip", f, "application/zip")}
            )
        
        # Assert
        assert response.status_code in [200, 201]
        data = response.json()
        assert "success" in data or "message" in data
    
    @pytest.mark.integration
    def test_import_providers_csv_endpoint(self, client, mock_csv_file):
        """Test /api/providers/import/csv endpoint."""
        # Act
        with open(mock_csv_file, 'rb') as f:
            response = client.post(
                "/api/providers/import/csv",
                files={"file": ("providers.csv", f, "text/csv")}
            )
        
        # Assert
        assert response.status_code in [200, 201]
        data = response.json()
        assert "created" in data or "success" in data
    
    @pytest.mark.integration
    def test_import_templates_endpoint(self, client, mock_json_template):
        """Test /api/templates/import endpoint."""
        # Act
        with open(mock_json_template, 'rb') as f:
            response = client.post(
                "/api/templates/import",
                files={"file": ("template.json", f, "application/json")}
            )
        
        # Assert
        assert response.status_code in [200, 201]
        data = response.json()
        assert "success" in data or "template_path" in data
    
    @pytest.mark.integration
    def test_import_with_invalid_file_type(self, client, temp_export_dir):
        """Test import endpoints reject invalid file types."""
        # Arrange - create a text file
        txt_file = os.path.join(temp_export_dir, "invalid.txt")
        with open(txt_file, 'w') as f:
            f.write("This is not a valid import file")
        
        # Act
        with open(txt_file, 'rb') as f:
            response = client.post(
                "/api/providers/import/csv",
                files={"file": ("invalid.txt", f, "text/plain")}
            )
        
        # Assert
        assert response.status_code in [400, 422]  # Bad request or unprocessable entity
