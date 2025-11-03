"""
Multi-tenant white-label configuration system
Manages tenant-specific branding, features, and settings
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

@dataclass
class TenantConfig:
    """Tenant configuration data structure"""
    tenant_id: str
    practice_name: str
    logo_url: str = ""
    primary_color: str = "#3B82F6"  # Default blue
    secondary_color: str = "#8B5CF6"  # Default purple
    features_enabled: Dict[str, bool] = None
    dentrix_bridge_url: str = "http://dentrix_bridge:8001"
    llm_provider: str = "ollama"
    whisper_model: str = "medium"
    subscription_tier: str = "free"
    is_active: bool = True
    created_at: str = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.features_enabled is None:
            self.features_enabled = {
                "ambient_scribe": True,
                "dentrix_integration": True,
                "voice_profiles": True,
                "openai_option": True,
                "email_system": True,
                "soap_templates": True
            }
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


class TenantConfigManager:
    """Manages tenant configurations"""
    
    def __init__(self, config_dir: str = "/app/config/tenants"):
        """
        Initialize tenant config manager
        
        Args:
            config_dir: Directory where tenant configs are stored
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"✅ Tenant config directory: {self.config_dir}")
    
    def load_tenant_config(self, tenant_id: str) -> TenantConfig:
        """
        Load tenant configuration from file
        
        Args:
            tenant_id: Unique tenant identifier
            
        Returns:
            TenantConfig object
            
        Raises:
            FileNotFoundError: If tenant config not found
            ValueError: If config is invalid
        """
        config_path = self.config_dir / f"{tenant_id}.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Tenant configuration not found for: {tenant_id}")
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            config = TenantConfig.from_dict(data)
            logging.info(f"✅ Loaded config for tenant: {tenant_id}")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tenant config for {tenant_id}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading tenant config for {tenant_id}: {e}")
    
    def save_tenant_config(self, config: TenantConfig) -> bool:
        """
        Save tenant configuration to file
        
        Args:
            config: TenantConfig object to save
            
        Returns:
            bool: True if successful
        """
        try:
            config_path = self.config_dir / f"{config.tenant_id}.json"
            
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            logging.info(f"✅ Saved config for tenant: {config.tenant_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving tenant config for {config.tenant_id}: {e}")
            return False
    
    def delete_tenant_config(self, tenant_id: str) -> bool:
        """
        Delete tenant configuration file
        
        Args:
            tenant_id: Unique tenant identifier
            
        Returns:
            bool: True if successful
        """
        try:
            config_path = self.config_dir / f"{tenant_id}.json"
            
            if config_path.exists():
                config_path.unlink()
                logging.info(f"✅ Deleted config for tenant: {tenant_id}")
                return True
            else:
                logging.warning(f"Config file not found for tenant: {tenant_id}")
                return False
                
        except Exception as e:
            logging.error(f"Error deleting tenant config for {tenant_id}: {e}")
            return False
    
    def list_tenant_ids(self) -> list:
        """
        List all tenant IDs
        
        Returns:
            list: List of tenant IDs
        """
        try:
            tenant_files = self.config_dir.glob("*.json")
            tenant_ids = [f.stem for f in tenant_files]
            return tenant_ids
        except Exception as e:
            logging.error(f"Error listing tenant IDs: {e}")
            return []
    
    def get_default_config(self) -> TenantConfig:
        """
        Get default tenant configuration template
        
        Returns:
            TenantConfig: Default configuration
        """
        return TenantConfig(
            tenant_id="default",
            practice_name="Dental Practice",
            logo_url="",
            primary_color="#3B82F6",
            secondary_color="#8B5CF6",
            features_enabled={
                "ambient_scribe": True,
                "dentrix_integration": True,
                "voice_profiles": True,
                "openai_option": True,
                "email_system": True,
                "soap_templates": True
            },
            dentrix_bridge_url="http://dentrix_bridge:8001",
            llm_provider="ollama",
            whisper_model="medium",
            subscription_tier="free",
            is_active=True
        )
    
    def tenant_exists(self, tenant_id: str) -> bool:
        """
        Check if tenant configuration exists
        
        Args:
            tenant_id: Unique tenant identifier
            
        Returns:
            bool: True if exists
        """
        config_path = self.config_dir / f"{tenant_id}.json"
        return config_path.exists()


# Global tenant config manager instance
tenant_manager = TenantConfigManager()
