#!/usr/bin/env python3
"""
Local test script for Boise Prosthodontics AI Scribe
Tests all components without requiring a browser
"""

import asyncio
import websockets
import json
import wave
import struct
import math
import io
import sys

def generate_test_audio(duration_seconds=5, sample_rate=16000):
    """Generate a test audio file with sine wave (simulates speech)"""
    num_samples = duration_seconds * sample_rate
    frequency = 440  # A4 note
    
    # Generate sine wave
    samples = []
    for i in range(num_samples):
        sample = 32767 * math.sin(2 * math.pi * frequency * i / sample_rate)
        samples.append(int(sample))
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Write samples
        for sample in samples:
            wav_file.writeframes(struct.pack('<h', sample))
    
    wav_buffer.seek(0)
    return wav_buffer.read()

async def test_websocket():
    """Test the WebSocket endpoint"""
    uri = "ws://localhost:4001/ws/audio"
    
    print("🔌 Connecting to WebSocket...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Generate test audio
            print("🎤 Generating test audio...")
            audio_data = generate_test_audio(duration_seconds=3)
            
            # Send audio in chunks
            print("📤 Sending audio chunks...")
            chunk_size = 1024
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await websocket.send(chunk)
                await asyncio.sleep(0.01)  # Small delay between chunks
            
            # Send END signal
            print("📤 Sending END signal...")
            await websocket.send("END")
            
            # Receive responses
            print("📥 Waiting for responses...")
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    
                    if isinstance(response, bytes):
                        print(f"🔊 Received audio data: {len(response)} bytes")
                    else:
                        data = json.loads(response)
                        print(f"📝 Received: {json.dumps(data, indent=2)}")
                        
                        if data.get("status") == "Complete":
                            print("\n✅ Test completed successfully!")
                            if "soap" in data:
                                print("\n📋 SOAP Note Preview:")
                                print("-" * 40)
                                print(data["soap"][:500] + "..." if len(data["soap"]) > 500 else data["soap"])
                            break
                        
                except asyncio.TimeoutError:
                    print("⏱️ Timeout waiting for response")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 Connection closed")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

async def test_health_endpoints():
    """Test REST API endpoints"""
    import aiohttp
    
    print("\n🏥 Testing health endpoints...")
    
    async with aiohttp.ClientSession() as session:
        # Test backend health
        try:
            async with session.get("http://localhost:4001/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Backend health: {data}")
                else:
                    print(f"❌ Backend health check failed: {resp.status}")
        except Exception as e:
            print(f"❌ Backend not reachable: {e}")
        
        # Test backend root
        try:
            async with session.get("http://localhost:4001/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Backend info: {data}")
        except Exception as e:
            print(f"❌ Backend root not reachable: {e}")

def test_mock_conversation():
    """Generate a mock conversation for testing"""
    mock_transcript = """
Doctor: Good morning, what brings you in today?
Patient: I've been having pain in my upper left molar for about a week now.
Doctor: On a scale of 1 to 10, how would you rate the pain?
Patient: It's about a 7, especially when I chew or drink cold liquids.
Doctor: Let me take a look. Please open wide. I can see some inflammation around tooth number 15.
Patient: Is it serious?
Doctor: There appears to be some decay. We'll need to take an X-ray to see the full extent.
Patient: Will I need a root canal?
Doctor: Let's get the X-ray first, then we'll discuss treatment options.
    """
    
    print("\n🎭 Mock Conversation Test")
    print("-" * 40)
    print(mock_transcript)
    print("-" * 40)
    
    expected_soap = """
Expected SOAP format:

SUBJECTIVE:
- Chief complaint: Pain in upper left molar for 1 week
- Pain scale: 7/10
- Aggravating factors: Chewing, cold liquids

OBJECTIVE:
- Visible inflammation around tooth #15
- Decay present
- X-ray ordered

ASSESSMENT:
- Dental decay with inflammation of tooth #15
- Possible pulpitis

PLAN:
- X-ray to assess extent of decay
- Discuss treatment options post-imaging
- Consider root canal vs restoration
    """
    
    print(expected_soap)
    return mock_transcript

async def main():
    """Run all tests"""
    print("🏥 Boise Prosthodontics AI Scribe - Local Test Suite")
    print("=" * 50)
    
    # Check if services are running
    print("\n1️⃣ Checking services...")
    import subprocess
    result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    if "boise_scribe_backend" not in result.stdout:
        print("❌ Backend container not running. Run: docker-compose up -d")
        sys.exit(1)
    print("✅ Docker containers are running")
    
    # Test health endpoints
    await test_health_endpoints()
    
    # Test WebSocket
    print("\n2️⃣ Testing WebSocket connection...")
    success = await test_websocket()
    
    if success:
        print("\n3️⃣ Mock conversation test...")
        test_mock_conversation()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("\nNext steps:")
        print("1. Open http://localhost:4000 in your browser")
        print("2. Test with a real microphone")
        print("3. Verify copy-to-clipboard functionality")
    else:
        print("\n❌ Tests failed. Check docker-compose logs for details.")
        print("Run: docker-compose logs -f backend")

if __name__ == "__main__":
    # Install required packages if needed
    try:
        import aiohttp
        import websockets
    except ImportError:
        print("Installing test dependencies...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "websockets"])
        print("Dependencies installed. Please run the script again.")
        sys.exit(0)
    
    asyncio.run(main())