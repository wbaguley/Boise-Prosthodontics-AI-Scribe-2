"""
Voice Profile Manager for Speaker Identification
Uses speaker embeddings to match voices to providers
"""

import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime
import logging
import torch
import torchaudio

logger = logging.getLogger(__name__)

class VoiceProfileManager:
    def __init__(self, profiles_dir="voice_profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Try to load embedding model (pyannote or fallback)
        self.embedding_model = None
        self.model_available = self._load_embedding_model()
        
    def _load_embedding_model(self):
        """Load speaker embedding model"""
        try:
            # Try pyannote first if HF_TOKEN is available
            import os
            hf_token = os.getenv('HF_TOKEN')
            
            if hf_token:
                from pyannote.audio import Model
                from pyannote.audio.pipelines import SpeakerEmbedding
                
                self.embedding_model = SpeakerEmbedding(
                    "pyannote/embedding",
                    use_auth_token=hf_token
                )
                logger.info("✅ Pyannote embedding model loaded")
                return True
            else:
                logger.warning("⚠️ No HF_TOKEN found, using simple voice profile")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Could not load embedding model: {e}")
            return False
    
    def create_profile(self, provider_name, audio_files):
        """
        Create voice profile from multiple audio samples
        
        Args:
            provider_name: Name of the provider
            audio_files: List of paths to audio files
            
        Returns:
            dict: Profile information with path
        """
        provider_dir = self.profiles_dir / provider_name.replace(" ", "_").lower()
        provider_dir.mkdir(exist_ok=True)
        
        embeddings = []
        
        if self.model_available and self.embedding_model:
            # Extract embeddings using pyannote
            for audio_file in audio_files:
                try:
                    embedding = self._extract_embedding_pyannote(audio_file)
                    if embedding is not None:
                        embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Error extracting embedding from {audio_file}: {e}")
        else:
            # Fallback: use simple audio features
            for audio_file in audio_files:
                try:
                    features = self._extract_simple_features(audio_file)
                    if features is not None:
                        embeddings.append(features)
                except Exception as e:
                    logger.error(f"Error extracting features from {audio_file}: {e}")
        
        if not embeddings:
            logger.error("No valid embeddings extracted")
            return None
        
        # Average embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        
        # Save profile
        profile = {
            'provider_name': provider_name,
            'embedding': avg_embedding.tolist(),
            'num_samples': len(embeddings),
            'created_at': datetime.now().isoformat(),
            'model_type': 'pyannote' if self.model_available else 'simple'
        }
        
        profile_path = provider_dir / 'profile.pkl'
        with open(profile_path, 'wb') as f:
            pickle.dump(profile, f)
        
        # Also save metadata as JSON
        metadata_path = provider_dir / 'metadata.json'
        metadata = {
            'provider_name': provider_name,
            'num_samples': len(embeddings),
            'created_at': profile['created_at'],
            'model_type': profile['model_type']
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Voice profile created for {provider_name}")
        return {
            'profile_path': str(profile_path),
            'provider_name': provider_name,
            'num_samples': len(embeddings)
        }
    
    def _extract_embedding_pyannote(self, audio_path):
        """Extract embedding using pyannote"""
        try:
            from pyannote.audio import Audio
            from pyannote.core import Segment
            
            audio = Audio(sample_rate=16000, mono=True)
            waveform, sample_rate = audio(audio_path)
            
            # Use full audio or first 10 seconds
            duration = min(10.0, waveform.shape[1] / sample_rate)
            segment = Segment(0, duration)
            
            embedding = self.embedding_model({
                'waveform': waveform,
                'sample_rate': sample_rate
            })
            
            return embedding
            
        except Exception as e:
            logger.error(f"Pyannote embedding error: {e}")
            return None
    
    def _extract_simple_features(self, audio_path):
        """Extract simple audio features as fallback"""
        try:
            # Load audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Convert to mono if needed
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Extract simple features: MFCC
            # FIXED: n_mfcc must be <= n_mels
            mfcc_transform = torchaudio.transforms.MFCC(
                sample_rate=sample_rate,
                n_mfcc=20,  # Changed from 40 to 20
                melkwargs={'n_fft': 400, 'hop_length': 160, 'n_mels': 40}  # Changed n_mels from 23 to 40
            )
            
            mfcc = mfcc_transform(waveform)
            
            # Average over time to get single feature vector
            features = torch.mean(mfcc, dim=2).squeeze().numpy()
            
            return features
            
        except Exception as e:
            logger.error(f"Simple feature extraction error: {e}")
            return None
    
    def identify_speaker(self, audio_path, candidate_providers=None):
        """
        Identify which provider is speaking in the audio
        
        Args:
            audio_path: Path to audio file
            candidate_providers: List of provider names to check (None = check all)
            
        Returns:
            dict: Best match with confidence score
        """
        if not candidate_providers:
            # Get all available profiles
            candidate_providers = [
                d.name.replace("_", " ").title() 
                for d in self.profiles_dir.iterdir() 
                if d.is_dir()
            ]
        
        if not candidate_providers:
            logger.warning("No voice profiles available")
            return None
        
        # Extract features from input audio
        if self.model_available and self.embedding_model:
            input_embedding = self._extract_embedding_pyannote(audio_path)
        else:
            input_embedding = self._extract_simple_features(audio_path)
        
        if input_embedding is None:
            return None
        
        # Compare with each candidate
        best_match = None
        best_score = -float('inf')
        
        for provider_name in candidate_providers:
            profile = self.load_profile(provider_name)
            if profile is None:
                continue
            
            stored_embedding = np.array(profile['embedding'])
            
            # Compute similarity (cosine similarity)
            similarity = self._cosine_similarity(input_embedding, stored_embedding)
            
            if similarity > best_score:
                best_score = similarity
                best_match = provider_name
        
        if best_match:
            return {
                'provider_name': best_match,
                'confidence': float(best_score),
                'threshold_met': best_score > 0.5  # Adjust threshold as needed
            }
        
        return None
    
    def _cosine_similarity(self, a, b):
        """Compute cosine similarity between two vectors"""
        a = np.array(a).flatten()
        b = np.array(b).flatten()
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def load_profile(self, provider_name):
        """Load voice profile for a provider"""
        provider_dir = self.profiles_dir / provider_name.replace(" ", "_").lower()
        profile_path = provider_dir / 'profile.pkl'
        
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'rb') as f:
                profile = pickle.load(f)
            return profile
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            return None
    
    def delete_profile(self, provider_name):
        """Delete voice profile for a provider"""
        provider_dir = self.profiles_dir / provider_name.replace(" ", "_").lower()
        
        if provider_dir.exists():
            import shutil
            shutil.rmtree(provider_dir)
            logger.info(f"Deleted voice profile for {provider_name}")
            return True
        
        return False
    
    def list_profiles(self):
        """List all available voice profiles"""
        profiles = []
        
        for provider_dir in self.profiles_dir.iterdir():
            if not provider_dir.is_dir():
                continue
            
            metadata_path = provider_dir / 'metadata.json'
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    profiles.append(metadata)
                except Exception as e:
                    logger.error(f"Error reading metadata for {provider_dir.name}: {e}")
        
        return profiles
    
    def get_profile_info(self, provider_name):
        """Get information about a voice profile"""
        provider_dir = self.profiles_dir / provider_name.replace(" ", "_").lower()
        metadata_path = provider_dir / 'metadata.json'
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading metadata: {e}")
        
        return None