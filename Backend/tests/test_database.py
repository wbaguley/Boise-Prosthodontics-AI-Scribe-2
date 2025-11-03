"""
Test suite for Database operations and API key encryption.
Tests CRUD operations, encryption, and database integrity.
"""
import pytest
from datetime import datetime
from database import (
    Provider, Session, Tenant, SystemConfig,
    create_provider, get_provider_by_id, get_all_providers,
    create_tenant, get_tenant_by_id, update_tenant, delete_tenant,
    EncryptionManager
)


class TestDatabaseCRUD:
    """Test cases for database CRUD operations."""
    
    # ========================================================================
    # Provider Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_create_provider_success(self, test_db, mock_provider_data):
        """Test successful provider creation."""
        # Act
        provider = create_provider(
            test_db,
            name=mock_provider_data["name"],
            specialty=mock_provider_data["specialty"],
            credentials=mock_provider_data["credentials"],
            email=mock_provider_data["email"],
            phone=mock_provider_data["phone"]
        )
        
        # Assert
        assert provider is not None
        assert provider.id > 0
        assert provider.name == mock_provider_data["name"]
        assert provider.specialty == mock_provider_data["specialty"]
    
    @pytest.mark.unit
    def test_get_provider_by_id_success(self, test_db, mock_provider_data):
        """Test retrieving provider by ID."""
        # Arrange
        provider = create_provider(test_db, **mock_provider_data)
        
        # Act
        retrieved = get_provider_by_id(test_db, provider.id)
        
        # Assert
        assert retrieved is not None
        assert retrieved.id == provider.id
        assert retrieved.name == provider.name
    
    @pytest.mark.unit
    def test_get_provider_by_id_not_found(self, test_db):
        """Test retrieving non-existent provider."""
        # Act
        provider = get_provider_by_id(test_db, 999999)
        
        # Assert
        assert provider is None
    
    @pytest.mark.unit
    def test_get_all_providers(self, test_db, mock_provider_data):
        """Test retrieving all providers."""
        # Arrange - create multiple providers
        for i in range(5):
            create_provider(test_db, **{**mock_provider_data, "name": f"Dr. Test {i}"})
        
        # Act
        providers = get_all_providers(test_db)
        
        # Assert
        assert len(providers) == 5
        assert all(isinstance(p, Provider) for p in providers)
    
    @pytest.mark.performance
    def test_create_many_providers_performance(self, test_db, mock_provider_data, performance_timer):
        """Test creating 100 providers completes within 2 seconds."""
        # Act
        performance_timer.start()
        for i in range(100):
            create_provider(test_db, **{**mock_provider_data, "name": f"Dr. Test {i}"})
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"Creating 100 providers took {performance_timer.elapsed}s"
        providers = get_all_providers(test_db)
        assert len(providers) == 100
    
    # ========================================================================
    # Session Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_create_session_success(self, test_db, mock_session_data, mock_provider_data):
        """Test successful session creation."""
        # Arrange
        provider = create_provider(test_db, **mock_provider_data)
        
        # Act
        session = Session(
            session_id=mock_session_data["session_id"],
            doctor=provider.name,
            provider_id=provider.id,
            transcript=mock_session_data["transcript"],
            soap_note=mock_session_data["soap_note"],
            template_used=mock_session_data["template_used"]
        )
        test_db.add(session)
        test_db.commit()
        
        # Assert
        assert session.id > 0
        assert session.provider_id == provider.id
        assert session.transcript == mock_session_data["transcript"]
    
    @pytest.mark.unit
    def test_session_provider_relationship(self, test_db, mock_session_data, mock_provider_data):
        """Test session-provider foreign key relationship."""
        # Arrange
        provider = create_provider(test_db, **mock_provider_data)
        session = Session(
            session_id=mock_session_data["session_id"],
            doctor=provider.name,
            provider_id=provider.id,
            transcript=mock_session_data["transcript"]
        )
        test_db.add(session)
        test_db.commit()
        
        # Act
        retrieved_session = test_db.query(Session).filter_by(session_id=mock_session_data["session_id"]).first()
        
        # Assert
        assert retrieved_session.provider_id == provider.id
        # Test relationship navigation
        assert retrieved_session.provider.name == provider.name
    
    # ========================================================================
    # Tenant Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_create_tenant_success(self, test_db, mock_tenant_data):
        """Test successful tenant creation."""
        # Act
        tenant = create_tenant(
            test_db,
            tenant_id=mock_tenant_data["tenant_id"],
            practice_name=mock_tenant_data["practice_name"],
            config_path=mock_tenant_data["config_path"],
            subscription_tier=mock_tenant_data["subscription_tier"]
        )
        
        # Assert
        assert tenant is not None
        assert tenant.tenant_id == mock_tenant_data["tenant_id"]
        assert tenant.practice_name == mock_tenant_data["practice_name"]
        assert tenant.is_active is True
    
    @pytest.mark.unit
    def test_get_tenant_by_id(self, test_db, mock_tenant_data):
        """Test retrieving tenant by ID."""
        # Arrange
        tenant = create_tenant(test_db, **mock_tenant_data)
        
        # Act
        retrieved = get_tenant_by_id(test_db, tenant.tenant_id)
        
        # Assert
        assert retrieved is not None
        assert retrieved.tenant_id == tenant.tenant_id
        assert retrieved.practice_name == tenant.practice_name
    
    @pytest.mark.unit
    def test_update_tenant(self, test_db, mock_tenant_data):
        """Test updating tenant information."""
        # Arrange
        tenant = create_tenant(test_db, **mock_tenant_data)
        
        # Act
        updated = update_tenant(
            test_db,
            tenant.tenant_id,
            practice_name="Updated Practice Name",
            subscription_tier="enterprise"
        )
        
        # Assert
        assert updated is not None
        assert updated.practice_name == "Updated Practice Name"
        assert updated.subscription_tier == "enterprise"
    
    @pytest.mark.unit
    def test_delete_tenant(self, test_db, mock_tenant_data):
        """Test tenant deletion (soft delete)."""
        # Arrange
        tenant = create_tenant(test_db, **mock_tenant_data)
        tenant_id = tenant.tenant_id
        
        # Act
        result = delete_tenant(test_db, tenant_id)
        
        # Assert
        assert result is True
        deleted_tenant = get_tenant_by_id(test_db, tenant_id)
        # Should be soft-deleted (is_active = False)
        assert deleted_tenant is None or deleted_tenant.is_active is False


class TestEncryption:
    """Test cases for API key encryption."""
    
    @pytest.fixture
    def encryption_manager(self):
        """Create EncryptionManager instance."""
        return EncryptionManager()
    
    # ========================================================================
    # Encryption/Decryption Tests
    # ========================================================================
    
    @pytest.mark.unit
    def test_encrypt_api_key_success(self, encryption_manager):
        """Test successful API key encryption."""
        # Arrange
        api_key = "sk-test1234567890abcdefghijklmnop"
        
        # Act
        encrypted = encryption_manager.encrypt(api_key)
        
        # Assert
        assert encrypted is not None
        assert isinstance(encrypted, bytes)
        assert encrypted != api_key.encode()
    
    @pytest.mark.unit
    def test_decrypt_api_key_success(self, encryption_manager):
        """Test successful API key decryption."""
        # Arrange
        api_key = "sk-test1234567890abcdefghijklmnop"
        encrypted = encryption_manager.encrypt(api_key)
        
        # Act
        decrypted = encryption_manager.decrypt(encrypted)
        
        # Assert
        assert decrypted == api_key
    
    @pytest.mark.unit
    def test_encrypt_decrypt_roundtrip(self, encryption_manager):
        """Test encrypt-decrypt roundtrip maintains data integrity."""
        # Arrange
        original_keys = [
            "sk-short",
            "sk-medium1234567890",
            "sk-verylongkeywithlotsofcharacters1234567890abcdefghijklmnopqrstuvwxyz",
            "sk-with-special-chars!@#$%^&*()_+-=[]{}|;:,.<>?"
        ]
        
        # Act & Assert
        for original in original_keys:
            encrypted = encryption_manager.encrypt(original)
            decrypted = encryption_manager.decrypt(encrypted)
            assert decrypted == original, f"Roundtrip failed for: {original}"
    
    @pytest.mark.unit
    def test_decrypt_with_invalid_data(self, encryption_manager):
        """Test decryption with invalid encrypted data."""
        # Arrange
        invalid_encrypted = b"not_valid_encrypted_data"
        
        # Act & Assert
        with pytest.raises(Exception):
            encryption_manager.decrypt(invalid_encrypted)
    
    @pytest.mark.unit
    def test_encrypt_empty_string(self, encryption_manager):
        """Test encryption of empty string."""
        # Act
        encrypted = encryption_manager.encrypt("")
        decrypted = encryption_manager.decrypt(encrypted)
        
        # Assert
        assert decrypted == ""
    
    @pytest.mark.performance
    def test_encryption_performance(self, encryption_manager, performance_timer):
        """Test 100 encryption operations complete within 2 seconds."""
        # Arrange
        api_key = "sk-test1234567890abcdefghijklmnop"
        
        # Act
        performance_timer.start()
        for _ in range(100):
            encrypted = encryption_manager.encrypt(api_key)
            decrypted = encryption_manager.decrypt(encrypted)
        performance_timer.stop()
        
        # Assert
        assert performance_timer.elapsed < 2.0, f"100 encrypt/decrypt ops took {performance_timer.elapsed}s"


class TestSystemConfig:
    """Test cases for SystemConfig table (API key storage)."""
    
    @pytest.mark.unit
    def test_store_encrypted_api_key(self, test_db, encryption_manager):
        """Test storing encrypted API key in SystemConfig."""
        # Arrange
        api_key = "sk-test1234567890"
        encrypted_key = encryption_manager.encrypt(api_key)
        
        # Act
        config = SystemConfig(
            key="openai_api_key",
            value=encrypted_key.decode('utf-8') if isinstance(encrypted_key, bytes) else encrypted_key
        )
        test_db.add(config)
        test_db.commit()
        
        # Assert
        retrieved = test_db.query(SystemConfig).filter_by(key="openai_api_key").first()
        assert retrieved is not None
        assert retrieved.value != api_key  # Should be encrypted
    
    @pytest.mark.unit
    def test_retrieve_and_decrypt_api_key(self, test_db, encryption_manager):
        """Test retrieving and decrypting API key from SystemConfig."""
        # Arrange
        api_key = "sk-test1234567890"
        encrypted_key = encryption_manager.encrypt(api_key)
        config = SystemConfig(key="openai_api_key", value=encrypted_key.hex())
        test_db.add(config)
        test_db.commit()
        
        # Act
        retrieved = test_db.query(SystemConfig).filter_by(key="openai_api_key").first()
        decrypted_key = encryption_manager.decrypt(bytes.fromhex(retrieved.value))
        
        # Assert
        assert decrypted_key == api_key
    
    @pytest.mark.unit
    def test_update_encrypted_api_key(self, test_db, encryption_manager):
        """Test updating encrypted API key."""
        # Arrange
        old_key = "sk-old-key"
        new_key = "sk-new-key"
        
        config = SystemConfig(
            key="openai_api_key",
            value=encryption_manager.encrypt(old_key).hex()
        )
        test_db.add(config)
        test_db.commit()
        
        # Act
        config.value = encryption_manager.encrypt(new_key).hex()
        test_db.commit()
        
        # Assert
        retrieved = test_db.query(SystemConfig).filter_by(key="openai_api_key").first()
        decrypted = encryption_manager.decrypt(bytes.fromhex(retrieved.value))
        assert decrypted == new_key
        assert decrypted != old_key
    
    @pytest.mark.unit
    def test_delete_api_key(self, test_db, encryption_manager):
        """Test deleting API key from SystemConfig."""
        # Arrange
        config = SystemConfig(
            key="openai_api_key",
            value=encryption_manager.encrypt("sk-test").hex()
        )
        test_db.add(config)
        test_db.commit()
        
        # Act
        test_db.delete(config)
        test_db.commit()
        
        # Assert
        retrieved = test_db.query(SystemConfig).filter_by(key="openai_api_key").first()
        assert retrieved is None


class TestDatabaseIntegrity:
    """Test cases for database integrity and constraints."""
    
    @pytest.mark.unit
    def test_unique_session_id_constraint(self, test_db, mock_session_data):
        """Test that duplicate session_id is prevented."""
        # Arrange
        session1 = Session(session_id="unique-123", doctor="Dr. Test")
        test_db.add(session1)
        test_db.commit()
        
        # Act & Assert
        session2 = Session(session_id="unique-123", doctor="Dr. Test2")
        test_db.add(session2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            test_db.commit()
    
    @pytest.mark.unit
    def test_cascade_delete_provider_sessions(self, test_db, mock_provider_data, mock_session_data):
        """Test cascade delete when provider is deleted."""
        # Arrange
        provider = create_provider(test_db, **mock_provider_data)
        session = Session(
            session_id=mock_session_data["session_id"],
            doctor=provider.name,
            provider_id=provider.id
        )
        test_db.add(session)
        test_db.commit()
        
        # Act
        test_db.delete(provider)
        test_db.commit()
        
        # Assert
        # Session should be deleted or have null provider_id (depending on cascade config)
        retrieved_session = test_db.query(Session).filter_by(session_id=mock_session_data["session_id"]).first()
        assert retrieved_session is None or retrieved_session.provider_id is None
    
    @pytest.mark.unit
    def test_tenant_foreign_key_integrity(self, test_db, mock_tenant_data, mock_provider_data):
        """Test tenant foreign key relationship with providers."""
        # Arrange
        tenant = create_tenant(test_db, **mock_tenant_data)
        provider = create_provider(test_db, **{**mock_provider_data, "tenant_id": tenant.tenant_id})
        
        # Assert
        assert provider.tenant_id == tenant.tenant_id
        
        # Test relationship navigation
        tenant_providers = test_db.query(Provider).filter_by(tenant_id=tenant.tenant_id).all()
        assert len(tenant_providers) == 1
        assert tenant_providers[0].name == provider.name
