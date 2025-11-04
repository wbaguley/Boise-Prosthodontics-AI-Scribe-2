"""
Whisper Model Pool for Concurrent Audio Processing
Pre-loads multiple Whisper models to handle simultaneous transcriptions
"""

import logging
import threading
import os
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperPool:
    """
    Pool of pre-loaded Whisper models for concurrent processing
    Allows multiple doctors to transcribe simultaneously
    """
    
    def __init__(self, pool_size: int = 3, model_size: str = "medium"):
        self.pool_size = pool_size
        self.model_size = model_size
        self.models = []
        self.available = []
        self.lock = threading.Lock()
        self.whisper = None
        self.torch = None
        
        logger.info(f"🔧 Initializing WhisperPool with {pool_size} models")
        self._load_models()
    
    def _load_models(self):
        """Pre-load Whisper models into the pool"""
        try:
            import whisper
            import torch
            
            self.whisper = whisper
            self.torch = torch
            
            # Set default dtype
            torch.set_default_dtype(torch.float32)
            
            logger.info(f"📥 Loading {self.pool_size} Whisper {self.model_size} models...")
            
            for i in range(self.pool_size):
                try:
                    model = whisper.load_model(self.model_size)
                    self.models.append(model)
                    self.available.append(i)
                    logger.info(f"✅ Loaded Whisper model {i+1}/{self.pool_size}")
                except Exception as e:
                    logger.error(f"❌ Failed to load Whisper model {i+1}: {e}")
            
            logger.info(f"🎯 WhisperPool ready with {len(self.models)} models")
            
        except ImportError:
            logger.warning("⚠️ Whisper not available - pool disabled")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WhisperPool: {e}")
    
    def acquire(self) -> Optional[any]:
        """
        Acquire a Whisper model from the pool
        Blocks if all models are in use
        
        Returns:
            Whisper model instance or None
        """
        if not self.models:
            logger.warning("⚠️ WhisperPool not available")
            return None
        
        while True:
            with self.lock:
                if self.available:
                    idx = self.available.pop(0)
                    model = self.models[idx]
                    logger.debug(f"🔓 Acquired Whisper model {idx}")
                    return (idx, model)
            
            # Wait a bit before checking again
            threading.Event().wait(0.1)
    
    def release(self, idx: int):
        """
        Release a Whisper model back to the pool
        
        Args:
            idx: Model index to release
        """
        with self.lock:
            if idx not in self.available and idx < len(self.models):
                self.available.append(idx)
                logger.debug(f"🔒 Released Whisper model {idx}")
    
    def transcribe_with_pool(self, audio_path: str, **kwargs) -> dict:
        """
        Transcribe audio using a model from the pool
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional arguments for transcribe()
        
        Returns:
            Transcription result
        """
        if not self.models:
            raise RuntimeError("WhisperPool not initialized")
        
        # Acquire model
        idx, model = self.acquire()
        
        try:
            # Transcribe
            logger.info(f"🎙️ Transcribing with model {idx}: {os.path.basename(audio_path)}")
            result = model.transcribe(audio_path, **kwargs)
            return result
        
        finally:
            # Always release model back to pool
            self.release(idx)
    
    def is_available(self) -> bool:
        """Check if pool has models available"""
        return len(self.models) > 0
    
    def get_stats(self) -> dict:
        """Get pool statistics"""
        with self.lock:
            return {
                "total_models": len(self.models),
                "available": len(self.available),
                "in_use": len(self.models) - len(self.available),
                "model_size": self.model_size
            }


# Global pool instance
whisper_pool = None


def get_whisper_pool(pool_size: int = 3, model_size: str = "medium") -> WhisperPool:
    """Get or create the global Whisper pool"""
    global whisper_pool
    
    if whisper_pool is None:
        whisper_pool = WhisperPool(pool_size=pool_size, model_size=model_size)
    
    return whisper_pool


def transcribe_audio(audio_path: str, **kwargs) -> Optional[dict]:
    """
    Convenience function to transcribe audio using the pool
    
    Args:
        audio_path: Path to audio file
        **kwargs: Additional transcription arguments
    
    Returns:
        Transcription result or None
    """
    pool = get_whisper_pool()
    
    if not pool.is_available():
        logger.error("Whisper pool not available")
        return None
    
    try:
        return pool.transcribe_with_pool(audio_path, **kwargs)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None
