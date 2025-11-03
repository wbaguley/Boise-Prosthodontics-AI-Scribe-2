"""
Test script for AudioProcessor
Demonstrates noise reduction, normalization, and quality checking
"""

import logging
import numpy as np
from scipy.io import wavfile
import tempfile
import os
from audio_processor import AudioProcessor, get_audio_processor

logging.basicConfig(level=logging.INFO)


def create_test_audio(filename: str, 
                     duration: float = 5.0,
                     sample_rate: int = 16000,
                     add_noise: bool = False) -> str:
    """
    Create a synthetic test audio file
    
    Args:
        filename: Output filename
        duration: Duration in seconds
        sample_rate: Sample rate
        add_noise: Add noise to the signal
        
    Returns:
        Path to created audio file
    """
    # Generate a simple sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # A4 note
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Add noise if requested
    if add_noise:
        noise = np.random.normal(0, 0.1, audio.shape)
        audio = audio + noise
    
    # Normalize to prevent clipping
    audio = audio * 0.5
    
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Save as WAV
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    wavfile.write(temp_path, sample_rate, audio_int16)
    
    print(f"✅ Created test audio: {temp_path}")
    return temp_path


def test_audio_processor():
    """Test all AudioProcessor functionality"""
    
    print("\n" + "="*70)
    print("🧪 TESTING AUDIO PROCESSOR")
    print("="*70)
    
    processor = AudioProcessor(
        enable_noise_reduction=True,
        enable_normalization=True,
        target_sample_rate=16000
    )
    
    # Test 1: Create clean audio
    print("\n📋 TEST 1: Clean Audio Quality Check")
    print("-" * 70)
    clean_audio = create_test_audio("test_clean.wav", duration=5.0, add_noise=False)
    quality = processor.check_audio_quality(clean_audio)
    
    print(f"\n📊 Quality Metrics:")
    print(f"  Valid: {quality['is_valid']}")
    print(f"  Sample Rate: {quality['sample_rate']} Hz")
    print(f"  Duration: {quality['duration']:.2f} seconds")
    print(f"  Channels: {quality['num_channels']}")
    print(f"  Amplitude Range: [{quality['amplitude_min']:.3f}, {quality['amplitude_max']:.3f}]")
    print(f"  Mean Amplitude: {quality['amplitude_mean']:.3f}")
    print(f"  Silent: {quality['is_silent']}")
    print(f"  Clipping: {quality['is_clipping']}")
    
    if quality['warnings']:
        print(f"\n⚠️ Warnings:")
        for warning in quality['warnings']:
            print(f"  - {warning}")
    
    if quality['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in quality['recommendations']:
            print(f"  - {rec}")
    
    # Test 2: Noisy audio with noise reduction
    print("\n📋 TEST 2: Noisy Audio + Noise Reduction")
    print("-" * 70)
    noisy_audio = create_test_audio("test_noisy.wav", duration=5.0, add_noise=True)
    
    print("\n🎯 Original noisy audio quality:")
    quality_before = processor.check_audio_quality(noisy_audio)
    print(f"  Mean Amplitude: {quality_before['amplitude_mean']:.3f}")
    
    print("\n🔄 Applying noise reduction...")
    cleaned_audio = processor.reduce_noise(noisy_audio)
    
    print("\n✅ Cleaned audio quality:")
    quality_after = processor.check_audio_quality(cleaned_audio)
    print(f"  Mean Amplitude: {quality_after['amplitude_mean']:.3f}")
    print(f"  Output: {cleaned_audio}")
    
    # Test 3: Different sample rates
    print("\n📋 TEST 3: Sample Rate Conversion")
    print("-" * 70)
    
    for rate in [8000, 22050, 44100]:
        print(f"\n🔄 Testing {rate}Hz audio...")
        test_audio = create_test_audio(f"test_{rate}hz.wav", 
                                       duration=3.0, 
                                       sample_rate=rate)
        quality = processor.check_audio_quality(test_audio)
        print(f"  Input: {rate}Hz")
        print(f"  Valid: {quality['is_valid']}")
        
        if quality['warnings']:
            for warning in quality['warnings']:
                print(f"  ⚠️ {warning}")
    
    # Test 4: Edge cases
    print("\n📋 TEST 4: Edge Cases")
    print("-" * 70)
    
    # Very short audio
    print("\n🔄 Testing very short audio (0.5s)...")
    short_audio = create_test_audio("test_short.wav", duration=0.5)
    quality_short = processor.check_audio_quality(short_audio)
    print(f"  Duration: {quality_short['duration']:.2f}s")
    print(f"  Valid: {quality_short['is_valid']}")
    
    # Silent audio
    print("\n🔄 Testing silent audio...")
    t = np.linspace(0, 3.0, int(16000 * 3.0))
    silent = np.zeros_like(t)
    silent_int16 = (silent * 32767).astype(np.int16)
    silent_path = os.path.join(tempfile.gettempdir(), "test_silent.wav")
    wavfile.write(silent_path, 16000, silent_int16)
    
    quality_silent = processor.check_audio_quality(silent_path)
    print(f"  Mean Amplitude: {quality_silent['amplitude_mean']:.6f}")
    print(f"  Is Silent: {quality_silent['is_silent']}")
    print(f"  Valid: {quality_silent['is_valid']}")
    
    # Test 5: Complete processing pipeline
    print("\n📋 TEST 5: Complete Processing Pipeline")
    print("-" * 70)
    noisy_test = create_test_audio("test_pipeline.wav", duration=5.0, add_noise=True)
    
    print("\n🔄 Running complete processing pipeline...")
    processed_path, quality_metrics = processor.process_audio(
        noisy_test,
        check_quality=True
    )
    
    print(f"\n✅ Processing complete!")
    print(f"  Input: {noisy_test}")
    print(f"  Output: {processed_path}")
    print(f"  Quality Valid: {quality_metrics['is_valid']}")
    print(f"  Duration: {quality_metrics['duration']:.2f}s")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    for file in [clean_audio, noisy_audio, cleaned_audio, short_audio, 
                silent_path, noisy_test, processed_path]:
        try:
            if os.path.exists(file):
                os.remove(file)
        except:
            pass
    
    # Also clean up sample rate test files
    for rate in [8000, 22050, 44100]:
        try:
            path = os.path.join(tempfile.gettempdir(), f"test_{rate}hz.wav")
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
    
    print("\n" + "="*70)
    print("✅ ALL AUDIO PROCESSOR TESTS COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_audio_processor()
