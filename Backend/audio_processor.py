"""
Audio Preprocessing Module for Noise Reduction and Quality Checking
Improves transcription accuracy by cleaning audio before processing
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Import audio processing libraries
try:
    import noisereduce as nr
    NOISE_REDUCE_AVAILABLE = True
    logger.info("✅ noisereduce library loaded successfully")
except ImportError:
    NOISE_REDUCE_AVAILABLE = False
    logger.warning("⚠️ noisereduce not available - install with: pip install noisereduce")

try:
    from scipy.io import wavfile
    import scipy.signal
    SCIPY_AVAILABLE = True
    logger.info("✅ scipy library loaded successfully")
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("⚠️ scipy not available - install with: pip install scipy")


class AudioProcessor:
    """
    Audio preprocessing for medical transcription
    
    Provides noise reduction, normalization, and quality checking
    to improve Whisper transcription accuracy.
    """
    
    # Audio quality thresholds
    RECOMMENDED_SAMPLE_RATE = 16000  # Whisper's native sample rate
    MINIMUM_DURATION = 1.0  # seconds
    MAXIMUM_DURATION = 3600.0  # 1 hour max
    MIN_AMPLITUDE_THRESHOLD = 0.001  # Detect silent audio
    MAX_AMPLITUDE_THRESHOLD = 0.95  # Detect clipping
    
    def __init__(self, 
                 enable_noise_reduction: bool = True,
                 enable_normalization: bool = True,
                 target_sample_rate: int = 16000):
        """
        Initialize audio processor
        
        Args:
            enable_noise_reduction: Apply noise reduction if True
            enable_normalization: Normalize audio levels if True
            target_sample_rate: Target sample rate for output (default: 16000)
        """
        self.enable_noise_reduction = enable_noise_reduction and NOISE_REDUCE_AVAILABLE
        self.enable_normalization = enable_normalization and SCIPY_AVAILABLE
        self.target_sample_rate = target_sample_rate
        
        if enable_noise_reduction and not NOISE_REDUCE_AVAILABLE:
            logger.warning("Noise reduction requested but noisereduce not available")
        
        if enable_normalization and not SCIPY_AVAILABLE:
            logger.warning("Normalization requested but scipy not available")
        
        logger.info(f"AudioProcessor initialized: noise_reduction={self.enable_noise_reduction}, "
                   f"normalization={self.enable_normalization}, target_rate={self.target_sample_rate}")
    
    def _load_audio(self, audio_path: str) -> Tuple[int, np.ndarray]:
        """
        Load audio file using scipy
        
        Args:
            audio_path: Path to WAV file
            
        Returns:
            Tuple of (sample_rate, audio_data)
            
        Raises:
            ValueError: If file cannot be loaded
        """
        if not SCIPY_AVAILABLE:
            raise ValueError("scipy is required for audio loading")
        
        if not os.path.exists(audio_path):
            raise ValueError(f"Audio file not found: {audio_path}")
        
        try:
            sample_rate, audio_data = wavfile.read(audio_path)
            logger.debug(f"Loaded audio: {audio_path}, rate={sample_rate}, shape={audio_data.shape}")
            return sample_rate, audio_data
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}")
            raise ValueError(f"Could not load audio file: {e}")
    
    def _save_audio(self, audio_path: str, sample_rate: int, audio_data: np.ndarray) -> str:
        """
        Save audio file using scipy
        
        Args:
            audio_path: Output path
            sample_rate: Sample rate
            audio_data: Audio data array
            
        Returns:
            Path to saved file
        """
        if not SCIPY_AVAILABLE:
            raise ValueError("scipy is required for audio saving")
        
        try:
            # Ensure audio is in correct format for WAV
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                # Convert float to int16 for WAV
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)
            
            wavfile.write(audio_path, sample_rate, audio_data)
            logger.debug(f"Saved audio: {audio_path}")
            return audio_path
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            raise ValueError(f"Could not save audio file: {e}")
    
    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio levels to optimal range
        
        Args:
            audio_data: Audio data array
            
        Returns:
            Normalized audio data
        """
        if not self.enable_normalization:
            return audio_data
        
        try:
            # Convert to float for processing
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Calculate peak amplitude
            max_amplitude = np.abs(audio_float).max()
            
            if max_amplitude > 0.0:
                # Normalize to 90% of maximum to avoid clipping
                target_amplitude = 0.9
                normalized = audio_float * (target_amplitude / max_amplitude)
                logger.debug(f"Normalized audio: peak {max_amplitude:.3f} -> {target_amplitude}")
                return normalized
            else:
                logger.warning("Audio has zero amplitude, cannot normalize")
                return audio_float
                
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, 
                       original_rate: int, 
                       target_rate: int) -> np.ndarray:
        """
        Resample audio to target sample rate
        
        Args:
            audio_data: Audio data array
            original_rate: Original sample rate
            target_rate: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if original_rate == target_rate:
            return audio_data
        
        if not SCIPY_AVAILABLE:
            logger.warning("Cannot resample without scipy, returning original")
            return audio_data
        
        try:
            # Calculate resampling ratio
            num_samples = int(len(audio_data) * target_rate / original_rate)
            resampled = scipy.signal.resample(audio_data, num_samples)
            logger.debug(f"Resampled audio: {original_rate}Hz -> {target_rate}Hz")
            return resampled
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            return audio_data
    
    def reduce_noise(self, audio_path: str) -> str:
        """
        Apply noise reduction to audio file
        
        Process:
        1. Load WAV file using scipy.io.wavfile
        2. Apply noise reduction using noisereduce
        3. Normalize audio levels
        4. Resample to target rate if needed
        5. Save cleaned audio to temp file with _clean suffix
        
        Args:
            audio_path: Path to input WAV file
            
        Returns:
            str: Path to cleaned audio file
            
        Raises:
            ValueError: If processing fails
        """
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available, returning original audio")
            return audio_path
        
        try:
            # Load audio
            sample_rate, audio_data = self._load_audio(audio_path)
            
            # Convert to float for processing
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Apply noise reduction if available
            if self.enable_noise_reduction and NOISE_REDUCE_AVAILABLE:
                logger.info("🎯 Applying noise reduction...")
                try:
                    # Use stationary noise reduction
                    audio_float = nr.reduce_noise(
                        y=audio_float,
                        sr=sample_rate,
                        stationary=True,
                        prop_decrease=0.8  # Reduce noise by 80%
                    )
                    logger.info("✅ Noise reduction applied successfully")
                except Exception as e:
                    logger.error(f"Noise reduction failed: {e}, using original audio")
            
            # Normalize audio levels
            if self.enable_normalization:
                logger.info("📊 Normalizing audio levels...")
                audio_float = self._normalize_audio(audio_float)
                logger.info("✅ Audio normalized")
            
            # Resample if needed
            if sample_rate != self.target_sample_rate:
                logger.info(f"🔄 Resampling: {sample_rate}Hz -> {self.target_sample_rate}Hz")
                audio_float = self._resample_audio(audio_float, sample_rate, self.target_sample_rate)
                sample_rate = self.target_sample_rate
                logger.info("✅ Audio resampled")
            
            # Generate output path with _clean suffix
            path_obj = Path(audio_path)
            clean_filename = f"{path_obj.stem}_clean{path_obj.suffix}"
            clean_path = str(path_obj.parent / clean_filename)
            
            # Save cleaned audio
            self._save_audio(clean_path, sample_rate, audio_float)
            
            logger.info(f"✅ Audio preprocessing complete: {clean_path}")
            return clean_path
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            logger.warning("Returning original audio due to processing error")
            return audio_path
    
    def check_audio_quality(self, audio_path: str) -> Dict:
        """
        Check audio quality and return metrics
        
        Checks:
        - Sample rate (should be 16000 for optimal Whisper performance)
        - Duration (minimum 1 second, maximum 1 hour)
        - Amplitude levels (detect silence or clipping)
        
        Args:
            audio_path: Path to WAV file
            
        Returns:
            dict: Quality metrics with keys:
                - is_valid: bool, overall quality assessment
                - sample_rate: int, actual sample rate
                - duration: float, duration in seconds
                - num_samples: int, total samples
                - num_channels: int, mono=1, stereo=2
                - amplitude_min: float, minimum amplitude
                - amplitude_max: float, maximum amplitude
                - amplitude_mean: float, mean amplitude
                - is_silent: bool, audio too quiet
                - is_clipping: bool, audio clipping detected
                - warnings: list of warning messages
                - recommendations: list of recommended actions
        """
        metrics = {
            'is_valid': False,
            'sample_rate': 0,
            'duration': 0.0,
            'num_samples': 0,
            'num_channels': 0,
            'amplitude_min': 0.0,
            'amplitude_max': 0.0,
            'amplitude_mean': 0.0,
            'is_silent': False,
            'is_clipping': False,
            'warnings': [],
            'recommendations': []
        }
        
        if not SCIPY_AVAILABLE:
            metrics['warnings'].append("scipy not available - cannot check audio quality")
            return metrics
        
        try:
            # Load audio
            sample_rate, audio_data = self._load_audio(audio_path)
            
            # Basic metrics
            metrics['sample_rate'] = sample_rate
            metrics['num_samples'] = len(audio_data)
            metrics['duration'] = len(audio_data) / sample_rate
            
            # Determine channels
            if len(audio_data.shape) == 1:
                metrics['num_channels'] = 1
                audio_mono = audio_data
            else:
                metrics['num_channels'] = audio_data.shape[1]
                # Convert to mono for analysis
                audio_mono = audio_data.mean(axis=1)
            
            # Convert to float for amplitude analysis
            if audio_mono.dtype == np.int16:
                audio_float = audio_mono.astype(np.float32) / 32768.0
            else:
                audio_float = audio_mono.astype(np.float32)
            
            # Amplitude metrics
            metrics['amplitude_min'] = float(audio_float.min())
            metrics['amplitude_max'] = float(audio_float.max())
            metrics['amplitude_mean'] = float(np.abs(audio_float).mean())
            
            # Quality checks
            
            # Check sample rate
            if sample_rate != self.RECOMMENDED_SAMPLE_RATE:
                metrics['warnings'].append(
                    f"Sample rate is {sample_rate}Hz (recommended: {self.RECOMMENDED_SAMPLE_RATE}Hz)"
                )
                metrics['recommendations'].append("Resample audio to 16000Hz for optimal Whisper performance")
            
            # Check duration
            if metrics['duration'] < self.MINIMUM_DURATION:
                metrics['warnings'].append(
                    f"Audio too short: {metrics['duration']:.1f}s (minimum: {self.MINIMUM_DURATION}s)"
                )
                metrics['is_valid'] = False
            elif metrics['duration'] > self.MAXIMUM_DURATION:
                metrics['warnings'].append(
                    f"Audio too long: {metrics['duration']:.1f}s (maximum: {self.MAXIMUM_DURATION}s)"
                )
                metrics['recommendations'].append("Consider splitting long audio into segments")
            
            # Check for silence
            if metrics['amplitude_mean'] < self.MIN_AMPLITUDE_THRESHOLD:
                metrics['is_silent'] = True
                metrics['warnings'].append("Audio appears to be silent or very quiet")
                metrics['recommendations'].append("Check microphone settings and increase recording volume")
                metrics['is_valid'] = False
            
            # Check for clipping
            max_abs_amplitude = max(abs(metrics['amplitude_min']), abs(metrics['amplitude_max']))
            if max_abs_amplitude > self.MAX_AMPLITUDE_THRESHOLD:
                metrics['is_clipping'] = True
                metrics['warnings'].append("Audio clipping detected (amplitude too high)")
                metrics['recommendations'].append("Reduce microphone gain to avoid distortion")
            
            # Check channels
            if metrics['num_channels'] > 1:
                metrics['warnings'].append(f"Audio has {metrics['num_channels']} channels (stereo)")
                metrics['recommendations'].append("Convert to mono for optimal processing")
            
            # Overall validity
            if (metrics['duration'] >= self.MINIMUM_DURATION and 
                metrics['duration'] <= self.MAXIMUM_DURATION and
                not metrics['is_silent']):
                metrics['is_valid'] = True
            
            logger.info(f"📊 Audio quality check complete: valid={metrics['is_valid']}, "
                       f"duration={metrics['duration']:.1f}s, rate={metrics['sample_rate']}Hz")
            
            if metrics['warnings']:
                for warning in metrics['warnings']:
                    logger.warning(f"⚠️ {warning}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Audio quality check failed: {e}")
            metrics['warnings'].append(f"Quality check failed: {str(e)}")
            return metrics
    
    def process_audio(self, audio_path: str, 
                     check_quality: bool = True) -> Tuple[str, Optional[Dict]]:
        """
        Complete audio processing pipeline
        
        Args:
            audio_path: Path to input audio file
            check_quality: Run quality check before processing
            
        Returns:
            Tuple of (processed_audio_path, quality_metrics or None)
        """
        quality_metrics = None
        
        # Check quality first
        if check_quality:
            logger.info("🔍 Checking audio quality...")
            quality_metrics = self.check_audio_quality(audio_path)
            
            if not quality_metrics['is_valid']:
                logger.warning("⚠️ Audio quality issues detected, but proceeding with processing")
        
        # Apply noise reduction and preprocessing
        logger.info("🎵 Processing audio...")
        cleaned_path = self.reduce_noise(audio_path)
        
        return cleaned_path, quality_metrics


# Singleton instance for easy access
_audio_processor = None

def get_audio_processor(enable_noise_reduction: bool = True,
                       enable_normalization: bool = True) -> AudioProcessor:
    """
    Get singleton AudioProcessor instance
    
    Args:
        enable_noise_reduction: Enable noise reduction
        enable_normalization: Enable normalization
        
    Returns:
        AudioProcessor: Shared processor instance
    """
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor(
            enable_noise_reduction=enable_noise_reduction,
            enable_normalization=enable_normalization
        )
    return _audio_processor


if __name__ == "__main__":
    # Test audio processor
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("🧪 AUDIO PROCESSOR TEST")
    print("="*70)
    
    processor = AudioProcessor()
    
    print(f"\n✅ Noise Reduction: {processor.enable_noise_reduction}")
    print(f"✅ Normalization: {processor.enable_normalization}")
    print(f"✅ Target Sample Rate: {processor.target_sample_rate}Hz")
    
    print("\n" + "="*70)
    print("📋 Dependencies:")
    print(f"  noisereduce: {'✅ Available' if NOISE_REDUCE_AVAILABLE else '❌ Not installed'}")
    print(f"  scipy: {'✅ Available' if SCIPY_AVAILABLE else '❌ Not installed'}")
    print("="*70 + "\n")
