#!/usr/bin/env python3
"""
Test script for voice recognition and provider management system
Run this to verify the system is working correctly
"""

import requests
import json
import sys
from pathlib import Path

API_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test if backend is running"""
    print_section("Testing Backend Health")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is running")
            print(f"   Status: {data.get('status')}")
            print(f"   Whisper: {data.get('whisper')}")
            print(f"   Diarization: {data.get('diarization')}")
            print(f"   Voice Profiles: {data.get('voice_profiles')}")
            print(f"   Ollama: {data.get('ollama')}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend")
        print("   Make sure docker-compose is running: docker-compose up -d")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_providers():
    """Test provider management"""
    print_section("Testing Provider Management")
    
    try:
        # Get all providers
        response = requests.get(f"{API_URL}/api/providers")
        if response.status_code == 200:
            providers = response.json()
            print(f"✅ Found {len(providers)} providers:")
            for provider in providers:
                voice_status = "🎤" if provider['has_voice_profile'] else "❌"
                print(f"   - {provider['name']} {voice_status}")
                if provider.get('specialty'):
                    print(f"     Specialty: {provider['specialty']}")
            
            if len(providers) == 0:
                print("\n⚠️  No providers found. Creating test provider...")
                test_create_provider()
            
            return True
        else:
            print(f"❌ Failed to get providers: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_provider():
    """Test creating a new provider"""
    print_section("Testing Provider Creation")
    
    test_provider = {
        "name": "Test Provider",
        "specialty": "Testing",
        "credentials": "TEST",
        "email": "test@example.com"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/providers",
            json=test_provider
        )
        
        if response.status_code == 200:
            provider = response.json()
            print(f"✅ Created provider: {provider['name']}")
            print(f"   ID: {provider['id']}")
            return provider
        else:
            error = response.json()
            if "already exists" in error.get('detail', '').lower():
                print("⚠️  Provider already exists (this is OK)")
                return None
            else:
                print(f"❌ Failed to create provider: {error.get('detail')}")
                return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_voice_profiles():
    """Test voice profile endpoints"""
    print_section("Testing Voice Profile System")
    
    try:
        response = requests.get(f"{API_URL}/api/voice-profiles")
        if response.status_code == 200:
            data = response.json()
            profiles = data.get('profiles', [])
            print(f"✅ Found {len(profiles)} voice profiles:")
            for profile in profiles:
                print(f"   - {profile['provider_name']}")
                print(f"     Created: {profile['created_at']}")
                print(f"     Samples: {profile['num_samples']}")
                print(f"     Model: {profile['model_type']}")
            
            if len(profiles) == 0:
                print("\n⚠️  No voice profiles found yet")
                print("   Use the UI to train voice profiles:")
                print("   1. Go to http://localhost:3000")
                print("   2. Select a provider")
                print("   3. Click the 🎤 icon")
                print("   4. Record training phrases")
            
            return True
        else:
            print(f"❌ Failed to get voice profiles: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_templates():
    """Test SOAP templates"""
    print_section("Testing SOAP Templates")
    
    try:
        response = requests.get(f"{API_URL}/api/templates")
        if response.status_code == 200:
            templates = response.json()
            print(f"✅ Found {len(templates)} templates:")
            for name, template in templates.items():
                print(f"   - {name}: {template.get('name', 'Unnamed')}")
            return True
        else:
            print(f"❌ Failed to get templates: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sessions():
    """Test session history"""
    print_section("Testing Session History")
    
    try:
        response = requests.get(f"{API_URL}/api/sessions")
        if response.status_code == 200:
            sessions = response.json()
            print(f"✅ Found {len(sessions)} sessions:")
            for session in sessions[:5]:  # Show first 5
                print(f"   - {session['session_id']}")
                print(f"     Doctor: {session['doctor']}")
                print(f"     Time: {session['timestamp']}")
            
            if len(sessions) == 0:
                print("\n⚠️  No sessions recorded yet")
            elif len(sessions) > 5:
                print(f"\n   ... and {len(sessions) - 5} more")
            
            return True
        else:
            print(f"❌ Failed to get sessions: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_websocket():
    """Test WebSocket connection (basic check)"""
    print_section("Testing WebSocket Connection")
    
    import socket
    
    try:
        # Try to connect to WebSocket port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result == 0:
            print("✅ WebSocket port is open")
            print("   Full WebSocket testing requires browser")
            print("   Test manually at: http://localhost:3000")
            return True
        else:
            print("❌ WebSocket port is not accessible")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database():
    """Test database connection"""
    print_section("Testing Database")
    
    # Check if database file exists
    db_path = Path("Backend/sessions.db")
    
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"✅ Database file exists")
        print(f"   Location: {db_path}")
        print(f"   Size: {size:,} bytes")
        return True
    else:
        print("❌ Database file not found")
        print("   Run: python Backend/init_database.py")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("  BOISE PROSTHODONTICS AI SCRIBE - SYSTEM TEST")
    print("="*60)
    
    tests = [
        ("Backend Health", test_health),
        ("Provider Management", test_providers),
        ("Voice Profiles", test_voice_profiles),
        ("SOAP Templates", test_templates),
        ("Session History", test_sessions),
        ("WebSocket Connection", test_websocket),
        ("Database", test_database)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Open http://localhost:3000 in your browser")
        print("2. Add providers if needed")
        print("3. Train voice profiles for each provider")
        print("4. Start recording consultations")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        print("\nCommon fixes:")
        print("- Ensure Docker is running: docker-compose up -d")
        print("- Check logs: docker-compose logs -f backend")
        print("- Initialize database: docker exec -it boise_backend python init_database.py")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)