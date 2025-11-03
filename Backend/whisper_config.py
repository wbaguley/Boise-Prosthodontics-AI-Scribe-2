"""
Whisper Model Configuration Manager
Manages Whisper model settings, downloads, and recommendations
"""

import os
import logging
import psutil
from pathlib import Path
from typing import Optional, Dict, List
import whisper

logger = logging.getLogger(__name__)


class WhisperConfig:
    """
    Configuration manager for Whisper speech recognition models
    
    Handles model selection, caching, downloading, and provides
    recommendations based on system resources.
    """
    
    # Model size specifications (approximate)
    MODEL_SPECS = {
        "tiny": {
            "parameters": "39M",
            "vram_required": "1 GB",
            "relative_speed": "32x",
            "download_size": "72 MB",
            "recommended_ram": 2,  # GB
            "description": "Fastest, lowest accuracy. Good for testing."
        },
        "base": {
            "parameters": "74M",
            "vram_required": "1 GB",
            "relative_speed": "16x",
            "download_size": "142 MB",
            "recommended_ram": 2,
            "description": "Fast with better accuracy than tiny."
        },
        "small": {
            "parameters": "244M",
            "vram_required": "2 GB",
            "relative_speed": "6x",
            "download_size": "466 MB",
            "recommended_ram": 4,
            "description": "Good balance of speed and accuracy."
        },
        "medium": {
            "parameters": "769M",
            "vram_required": "5 GB",
            "relative_speed": "2x",
            "download_size": "1.42 GB",
            "recommended_ram": 8,
            "description": "High accuracy, moderate speed. Recommended for medical transcription."
        },
        "large-v3": {
            "parameters": "1550M",
            "vram_required": "10 GB",
            "relative_speed": "1x",
            "download_size": "2.87 GB",
            "recommended_ram": 16,
            "description": "Highest accuracy, slowest. Best for critical medical documentation."
        }
    }
    
    # Supported languages
    SUPPORTED_LANGUAGES = [
        "en",  # English
        "es",  # Spanish
        "fr",  # French
        "de",  # German
        "it",  # Italian
        "pt",  # Portuguese
        "nl",  # Dutch
        "ja",  # Japanese
        "ko",  # Korean
        "zh",  # Chinese
    ]
    
    # Compute types for optimization
    COMPUTE_TYPES = {
        "int8": "8-bit integer (fastest, lowest memory, slight accuracy loss)",
        "float16": "16-bit floating point (GPU accelerated, good balance)",
        "float32": "32-bit floating point (highest accuracy, slower)"
    }
    
    def __init__(
        self,
        model_size: str = "medium",
        language: str = "en",
        compute_type: str = "float16",
        cache_dir: Optional[str] = None
    ):
        """
        Initialize Whisper configuration
        
        Args:
            model_size: Size of the model (tiny/base/small/medium/large-v3)
            language: Language code for transcription
            compute_type: Precision type (int8/float16/float32)
            cache_dir: Directory to cache models (default: ~/.cache/whisper)
        """
        self.model_size = self._validate_model_size(model_size)
        self.language = self._validate_language(language)
        self.compute_type = self._validate_compute_type(compute_type)
        self.cache_dir = Path(cache_dir) if cache_dir else self._get_default_cache_dir()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Whisper Config initialized: {self.model_size} model, {self.language} language, {self.compute_type} compute")
    
    def _validate_model_size(self, model_size: str) -> str:
        """Validate model size parameter"""
        if model_size not in self.MODEL_SPECS:
            valid_sizes = ", ".join(self.MODEL_SPECS.keys())
            raise ValueError(f"Invalid model size '{model_size}'. Valid options: {valid_sizes}")
        return model_size
    
    def _validate_language(self, language: str) -> str:
        """Validate language parameter"""
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Language '{language}' may not be fully supported. Using anyway.")
        return language
    
    def _validate_compute_type(self, compute_type: str) -> str:
        """Validate compute type parameter"""
        if compute_type not in self.COMPUTE_TYPES:
            valid_types = ", ".join(self.COMPUTE_TYPES.keys())
            logger.warning(f"Unknown compute type '{compute_type}'. Valid options: {valid_types}")
        return compute_type
    
    def _get_default_cache_dir(self) -> Path:
        """Get default cache directory for Whisper models"""
        # Try to use XDG_CACHE_HOME or default to ~/.cache
        cache_home = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))
        return Path(cache_home) / 'whisper'
    
    def get_model_path(self) -> str:
        """
        Get the path where the model is cached
        
        Returns:
            str: Path to the cached model file
        """
        model_file = f"{self.model_size}.pt"
        return str(self.cache_dir / model_file)
    
    def is_model_downloaded(self) -> bool:
        """
        Check if the model is already downloaded
        
        Returns:
            bool: True if model exists in cache
        """
        model_path = self.get_model_path()
        exists = os.path.exists(model_path)
        
        if exists:
            # Verify file size is reasonable
            file_size = os.path.getsize(model_path)
            if file_size < 1000000:  # Less than 1MB is suspicious
                logger.warning(f"Model file exists but seems corrupted (size: {file_size} bytes)")
                return False
        
        return exists
    
    def download_model_if_needed(self) -> bool:
        """
        Download the model if it's not already cached
        
        Returns:
            bool: True if model is ready (was already downloaded or just downloaded)
        """
        if self.is_model_downloaded():
            logger.info(f"Model '{self.model_size}' already downloaded at {self.get_model_path()}")
            return True
        
        try:
            logger.info(f"Downloading Whisper '{self.model_size}' model...")
            logger.info(f"Download size: {self.MODEL_SPECS[self.model_size]['download_size']}")
            
            # Use whisper's built-in download
            whisper.load_model(self.model_size, download_root=str(self.cache_dir))
            
            logger.info(f"✅ Model '{self.model_size}' downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download model '{self.model_size}': {e}")
            return False
    
    def get_system_ram_gb(self) -> float:
        """
        Get total system RAM in GB
        
        Returns:
            float: Total RAM in gigabytes
        """
        try:
            total_ram = psutil.virtual_memory().total
            return total_ram / (1024 ** 3)  # Convert bytes to GB
        except Exception as e:
            logger.error(f"Error detecting system RAM: {e}")
            return 0.0
    
    def get_available_ram_gb(self) -> float:
        """
        Get available system RAM in GB
        
        Returns:
            float: Available RAM in gigabytes
        """
        try:
            available_ram = psutil.virtual_memory().available
            return available_ram / (1024 ** 3)  # Convert bytes to GB
        except Exception as e:
            logger.error(f"Error detecting available RAM: {e}")
            return 0.0
    
    def recommend_model_size(self) -> Dict[str, any]:
        """
        Recommend model size based on available system resources
        
        Returns:
            dict: Recommendation with model size and reasoning
        """
        total_ram = self.get_system_ram_gb()
        available_ram = self.get_available_ram_gb()
        
        # Determine recommended model based on RAM
        if total_ram >= 16:
            recommended = "large-v3"
            reason = "System has sufficient RAM (16+ GB) for highest accuracy model"
        elif total_ram >= 8:
            recommended = "medium"
            reason = "System has 8+ GB RAM, medium model provides excellent accuracy"
        elif total_ram >= 4:
            recommended = "small"
            reason = "System has 4+ GB RAM, small model balances speed and accuracy"
        elif total_ram >= 2:
            recommended = "base"
            reason = "Limited RAM (2-4 GB), base model recommended"
        else:
            recommended = "tiny"
            reason = "Very limited RAM (<2 GB), tiny model required"
        
        return {
            "recommended_model": recommended,
            "current_model": self.model_size,
            "total_ram_gb": round(total_ram, 2),
            "available_ram_gb": round(available_ram, 2),
            "reason": reason,
            "is_optimal": self.model_size == recommended,
            "model_specs": self.MODEL_SPECS[recommended]
        }
    
    def get_all_model_info(self) -> List[Dict]:
        """
        Get information about all available models
        
        Returns:
            list: List of dictionaries with model information
        """
        models_info = []
        
        for model_name, specs in self.MODEL_SPECS.items():
            model_path = str(self.cache_dir / f"{model_name}.pt")
            is_downloaded = os.path.exists(model_path)
            
            models_info.append({
                "name": model_name,
                "parameters": specs["parameters"],
                "vram_required": specs["vram_required"],
                "download_size": specs["download_size"],
                "relative_speed": specs["relative_speed"],
                "recommended_ram_gb": specs["recommended_ram"],
                "description": specs["description"],
                "is_downloaded": is_downloaded,
                "is_current": model_name == self.model_size
            })
        
        return models_info
    
    def get_config_summary(self) -> Dict:
        """
        Get a summary of the current configuration
        
        Returns:
            dict: Configuration summary
        """
        return {
            "model_size": self.model_size,
            "language": self.language,
            "compute_type": self.compute_type,
            "cache_dir": str(self.cache_dir),
            "model_path": self.get_model_path(),
            "is_downloaded": self.is_model_downloaded(),
            "model_specs": self.MODEL_SPECS[self.model_size],
            "compute_type_info": self.COMPUTE_TYPES.get(self.compute_type, "Unknown"),
            "recommendation": self.recommend_model_size()
        }
    
    def print_config_summary(self):
        """Print a formatted configuration summary"""
        summary = self.get_config_summary()
        
        print("\n" + "="*60)
        print("🎤 WHISPER MODEL CONFIGURATION")
        print("="*60)
        print(f"\nCurrent Model: {summary['model_size'].upper()}")
        print(f"Language: {summary['language']}")
        print(f"Compute Type: {summary['compute_type']}")
        print(f"Downloaded: {'✅ Yes' if summary['is_downloaded'] else '❌ No'}")
        print(f"\nModel Specifications:")
        print(f"  Parameters: {summary['model_specs']['parameters']}")
        print(f"  Download Size: {summary['model_specs']['download_size']}")
        print(f"  VRAM Required: {summary['model_specs']['vram_required']}")
        print(f"  Speed: {summary['model_specs']['relative_speed']}")
        print(f"  Description: {summary['model_specs']['description']}")
        
        rec = summary['recommendation']
        print(f"\n💡 System Recommendation:")
        print(f"  Total RAM: {rec['total_ram_gb']} GB")
        print(f"  Available RAM: {rec['available_ram_gb']} GB")
        print(f"  Recommended Model: {rec['recommended_model'].upper()}")
        print(f"  Reason: {rec['reason']}")
        print(f"  Using Optimal Model: {'✅ Yes' if rec['is_optimal'] else '⚠️ No'}")
        print("="*60 + "\n")
    
    def update_model_size(self, new_size: str) -> bool:
        """
        Update the model size configuration
        
        Args:
            new_size: New model size to use
            
        Returns:
            bool: True if update successful
        """
        try:
            validated_size = self._validate_model_size(new_size)
            old_size = self.model_size
            self.model_size = validated_size
            
            logger.info(f"Model size updated from '{old_size}' to '{new_size}'")
            return True
            
        except ValueError as e:
            logger.error(f"Failed to update model size: {e}")
            return False
    
    @classmethod
    def from_env(cls) -> 'WhisperConfig':
        """
        Create WhisperConfig instance from environment variables
        
        Environment variables:
            WHISPER_MODEL: Model size (default: medium)
            WHISPER_LANGUAGE: Language code (default: en)
            WHISPER_COMPUTE_TYPE: Compute type (default: float16)
            WHISPER_CACHE_DIR: Cache directory (optional)
        
        Returns:
            WhisperConfig: Configured instance
        """
        model_size = os.getenv('WHISPER_MODEL', 'medium')
        language = os.getenv('WHISPER_LANGUAGE', 'en')
        compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'float16')
        cache_dir = os.getenv('WHISPER_CACHE_DIR', None)
        
        return cls(
            model_size=model_size,
            language=language,
            compute_type=compute_type,
            cache_dir=cache_dir
        )


# Convenience function for quick access
def get_whisper_config() -> WhisperConfig:
    """
    Get WhisperConfig instance from environment variables
    
    Returns:
        WhisperConfig: Configured instance
    """
    return WhisperConfig.from_env()


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("\n🔍 Testing Whisper Configuration Manager\n")
    
    # Create config from environment
    config = WhisperConfig.from_env()
    
    # Print configuration summary
    config.print_config_summary()
    
    # Show all available models
    print("\n📋 All Available Models:")
    print("="*60)
    for model_info in config.get_all_model_info():
        status = "✅ Downloaded" if model_info['is_downloaded'] else "⬇️ Not Downloaded"
        current = " (CURRENT)" if model_info['is_current'] else ""
        print(f"\n{model_info['name'].upper()}{current}")
        print(f"  Status: {status}")
        print(f"  Size: {model_info['download_size']}")
        print(f"  RAM: {model_info['recommended_ram_gb']} GB")
        print(f"  Speed: {model_info['relative_speed']}")
        print(f"  {model_info['description']}")
    
    print("\n" + "="*60 + "\n")
