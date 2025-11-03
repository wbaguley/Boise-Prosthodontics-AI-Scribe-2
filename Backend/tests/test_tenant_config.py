"""
Test suite for Tenant Configuration functionality.
Tests multi-tenant white-label system.
"""
import pytest
import json
import os
from tenant_config import TenantConfig, TenantConfigManager


class TestTenantConfig:
    """Test cases for TenantConfig dataclass."""
    
    @pytest.mark.unit
    def test_tenant_config_creation_success(self, mock_tenant_config):
        """Test successful creation of TenantConfig."""
        # Act
        config = TenantConfig(**mock_tenant_config)
        
        # Assert
        assert config.practice_name == "Test Dental Practice"
        assert config.logo_url == "https://example.com/logo.png"
        assert config.primary_color == "#1E40AF"
        assert config.features_enabled["ambient_scribe"] is True
    
    @pytest.mark.unit
    def test_tenant_config_with_missing_data(self):
        """Test TenantConfig with minimal data."""
        # Arrange
        minimal_config = {
            "practice_name": "Test Practice"
        }
        
        # Act
        config = TenantConfig(**minimal_config)
        
        # Assert
        assert config.practice_name == "Test Practice"
        # Should have defaults for other fields
    
    @pytest.mark.unit
    def test_tenant_config_serialization(self, mock_tenant_config):
        """Test TenantConfig can be serialized to dict."""
        # Arrange
        config = TenantConfig(**mock_tenant_config)
        
        # Act
        config_dict = config.__dict__
        
        # Assert
        assert isinstance(config_dict, dict)
        assert config_dict["practice_name"] == "Test Dental Practice"


class TestTenantConfigManager:
    """Test cases for TenantConfigManager class."""
    
    @pytest.fixture
    def config_manager(self, temp_export_dir):
        """Create TenantConfigManager with temp directory."""
        return TenantConfigManager(config_dir=temp_export_dir)
    
    # ========================================================================
    # Load/Save Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_save_tenant_config_success(self, config_manager, mock_tenant_config):
        """Test successful saving of tenant configuration."""
        # Arrange
        config = TenantConfig(**mock_tenant_config)
        tenant_id = 1
        
        # Act
        result = config_manager.save_tenant_config(tenant_id, config)
        
        # Assert
        assert result is True
        config_path = os.path.join(config_manager.config_dir, f"{tenant_id}.json")
        assert os.path.exists(config_path)
        
        # Verify content
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        assert saved_data["practice_name"] == "Test Dental Practice"
    
    @pytest.mark.unit
    def test_load_tenant_config_success(self, config_manager, mock_tenant_config):
        """Test successful loading of tenant configuration."""
        # Arrange - save a config first
        config = TenantConfig(**mock_tenant_config)
        tenant_id = 1
        config_manager.save_tenant_config(tenant_id, config)
        
        # Act
        loaded_config = config_manager.load_tenant_config(tenant_id)
        
        # Assert
        assert loaded_config is not None
        assert loaded_config.practice_name == "Test Dental Practice"
        assert loaded_config.features_enabled["ambient_scribe"] is True
    
    @pytest.mark.unit
    def test_load_tenant_config_with_missing_file(self, config_manager):
        """Test loading non-existent tenant configuration."""
        # Act
        loaded_config = config_manager.load_tenant_config(999)
        
        # Assert
        assert loaded_config is None  # Should return None or default config
    
    @pytest.mark.unit
    def test_load_tenant_config_with_invalid_json(self, config_manager, temp_export_dir):
        """Test loading tenant config with corrupted JSON."""
        # Arrange - create invalid JSON file
        config_path = os.path.join(temp_export_dir, "1.json")
        with open(config_path, 'w') as f:
            f.write("{invalid json")
        
        # Act & Assert
        with pytest.raises(Exception):
            config_manager.load_tenant_config(1)
    
    @pytest.mark.performance
    def test_load_tenant_config_performance(self, config_manager, mock_tenant_config, performance_timer):
        """Test tenant config loading completes within 2 seconds."""
        # Arrange
        config = TenantConfig(**mock_tenant_config)
        config_manager.save_tenant_config(1, config)
        
        # Act
        performance_timer.start()
        loaded_config = config_manager.load_tenant_config(1)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"Load took {performance_timer.elapsed}s, expected < 2s"
        assert loaded_config is not None
    
    # ========================================================================
    # Delete/List Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_delete_tenant_config_success(self, config_manager, mock_tenant_config):
        """Test successful deletion of tenant configuration."""
        # Arrange
        config = TenantConfig(**mock_tenant_config)
        tenant_id = 1
        config_manager.save_tenant_config(tenant_id, config)
        
        # Act
        result = config_manager.delete_tenant_config(tenant_id)
        
        # Assert
        assert result is True
        config_path = os.path.join(config_manager.config_dir, f"{tenant_id}.json")
        assert not os.path.exists(config_path)
    
    @pytest.mark.unit
    def test_delete_nonexistent_tenant_config(self, config_manager):
        """Test deleting non-existent tenant configuration."""
        # Act
        result = config_manager.delete_tenant_config(999)
        
        # Assert
        assert result is False  # Should return False for non-existent config
    
    @pytest.mark.unit
    def test_list_tenant_configs(self, config_manager, mock_tenant_config):
        """Test listing all tenant configurations."""
        # Arrange - create multiple configs
        for i in range(1, 4):
            config = TenantConfig(**{**mock_tenant_config, "practice_name": f"Practice {i}"})
            config_manager.save_tenant_config(i, config)
        
        # Act
        tenant_ids = config_manager.list_tenant_configs()
        
        # Assert
        assert len(tenant_ids) == 3
        assert 1 in tenant_ids
        assert 2 in tenant_ids
        assert 3 in tenant_ids


class TestTenantAPIEndpoints:
    """Test cases for tenant management API endpoints."""
    
    @pytest.mark.integration
    def test_create_tenant_endpoint(self, client, mock_tenant_data):
        """Test POST /api/admin/tenants endpoint."""
        # Act
        response = client.post("/api/admin/tenants", json=mock_tenant_data)
        
        # Assert
        assert response.status_code in [200, 201]
        data = response.json()
        assert "tenant_id" in data or "id" in data
    
    @pytest.mark.integration
    def test_get_tenant_endpoint(self, client, test_db, mock_tenant_data):
        """Test GET /api/admin/tenants/{tenant_id} endpoint."""
        # Arrange - create a tenant
        from database import Tenant
        tenant = Tenant(**mock_tenant_data)
        test_db.add(tenant)
        test_db.commit()
        
        # Act
        response = client.get(f"/api/admin/tenants/{tenant.tenant_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["practice_name"] == "Test Dental Practice"
    
    @pytest.mark.integration
    def test_list_tenants_endpoint(self, client, test_db, mock_tenant_data):
        """Test GET /api/admin/tenants endpoint."""
        # Arrange - create multiple tenants
        from database import Tenant
        for i in range(3):
            tenant = Tenant(**{**mock_tenant_data, "tenant_id": i + 1, "practice_name": f"Practice {i}"})
            test_db.add(tenant)
        test_db.commit()
        
        # Act
        response = client.get("/api/admin/tenants")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
    
    @pytest.mark.integration
    def test_update_tenant_endpoint(self, client, test_db, mock_tenant_data):
        """Test PUT /api/admin/tenants/{tenant_id} endpoint."""
        # Arrange
        from database import Tenant
        tenant = Tenant(**mock_tenant_data)
        test_db.add(tenant)
        test_db.commit()
        
        updated_data = {**mock_tenant_data, "practice_name": "Updated Practice Name"}
        
        # Act
        response = client.put(f"/api/admin/tenants/{tenant.tenant_id}", json=updated_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["practice_name"] == "Updated Practice Name"
    
    @pytest.mark.integration
    def test_delete_tenant_endpoint(self, client, test_db, mock_tenant_data):
        """Test DELETE /api/admin/tenants/{tenant_id} endpoint."""
        # Arrange
        from database import Tenant
        tenant = Tenant(**mock_tenant_data)
        test_db.add(tenant)
        test_db.commit()
        tenant_id = tenant.tenant_id
        
        # Act
        response = client.delete(f"/api/admin/tenants/{tenant_id}")
        
        # Assert
        assert response.status_code in [200, 204]
        
        # Verify deletion
        tenant = test_db.query(Tenant).filter_by(tenant_id=tenant_id).first()
        assert tenant is None or tenant.is_active is False
    
    @pytest.mark.integration
    def test_get_nonexistent_tenant(self, client):
        """Test getting non-existent tenant returns 404."""
        # Act
        response = client.get("/api/admin/tenants/999999")
        
        # Assert
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_tenant_middleware(self, client, test_db, mock_tenant_data):
        """Test tenant middleware extracts tenant_id from headers."""
        # Arrange
        from database import Tenant
        tenant = Tenant(**mock_tenant_data)
        test_db.add(tenant)
        test_db.commit()
        
        # Act - make request with X-Tenant-ID header
        response = client.get(
            "/api/config",
            headers={"X-Tenant-ID": str(tenant.tenant_id)}
        )
        
        # Assert
        assert response.status_code == 200
        # Response should include tenant-specific configuration
