#!/usr/bin/env python3
"""
Test script for the new SOAP chat editing feature
"""

import requests
import json

API_URL = "http://localhost:3051"

def test_chat_endpoint():
    """Test the new chat endpoint"""
    
    # Sample SOAP note for testing
    sample_soap = """SUBJECTIVE:
- Chief Complaint: Patient reports pain in upper left molar
- Duration: 1 week
- Pain level: 7/10

OBJECTIVE:
- Tooth #14 shows signs of failed crown
- Inflammation around gingival margin
- No visible caries on adjacent teeth

ASSESSMENT:
- Failed crown on tooth #14
- Secondary diagnosis: Possible endodontic involvement

PLAN:
- Remove existing crown
- Evaluate for endodontic treatment
- Prepare new crown if pulp is vital"""
    
    sample_transcript = "Doctor: Good morning, what brings you in today? Patient: I've been having pain in my upper left molar..."
    
    # Test data
    test_data = {
        "original_soap": sample_soap,
        "transcript": sample_transcript,
        "user_message": "Can you add that the patient has a history of grinding their teeth?",
        "chat_history": []
    }
    
    try:
        print("Testing SOAP chat editing endpoint...")
        response = requests.post(
            f"{API_URL}/api/edit-soap-chat",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat endpoint test successful!")
            print(f"AI Response: {result.get('ai_response', 'No response')}")
            print(f"SOAP Modified: {result.get('soap_modified', False)}")
            if result.get('soap_modified'):
                print("Updated SOAP Note:")
                print(result.get('updated_soap', 'No updated SOAP'))
        else:
            print(f"❌ Chat endpoint test failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server. Make sure it's running on localhost:3051")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

def test_question_vs_modification():
    """Test that the system can distinguish between questions and modification requests"""
    
    sample_soap = """SUBJECTIVE:
- Chief Complaint: Routine cleaning

OBJECTIVE:
- No visible decay
- Mild plaque buildup

ASSESSMENT:
- Good oral health

PLAN:
- Regular cleaning
- 6-month follow-up"""
    
    # Test question (should not modify SOAP)
    question_data = {
        "original_soap": sample_soap,
        "transcript": "Standard cleaning visit",
        "user_message": "What does this SOAP note tell us about the patient's oral health?",
        "chat_history": []
    }
    
    # Test modification request (should modify SOAP)
    modification_data = {
        "original_soap": sample_soap,
        "transcript": "Standard cleaning visit", 
        "user_message": "Please add that we recommended a fluoride treatment",
        "chat_history": []
    }
    
    try:
        print("\nTesting question handling...")
        response = requests.post(f"{API_URL}/api/edit-soap-chat", json=question_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            should_not_modify = not result.get('soap_modified', True)
            print(f"✅ Question test {'passed' if should_not_modify else 'failed'} - SOAP modified: {result.get('soap_modified')}")
        
        print("\nTesting modification handling...")
        response = requests.post(f"{API_URL}/api/edit-soap-chat", json=modification_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            should_modify = result.get('soap_modified', False)
            print(f"✅ Modification test {'passed' if should_modify else 'failed'} - SOAP modified: {result.get('soap_modified')}")
            
    except Exception as e:
        print(f"❌ Intent test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing SOAP Chat Feature")
    print("=" * 50)
    
    test_chat_endpoint()
    test_question_vs_modification()
    
    print("\n📝 Manual Testing Instructions:")
    print("1. Start the backend server: python backend/main.py")
    print("2. Start the frontend: npm start")
    print("3. Record a conversation to generate a SOAP note")
    print("4. Click 'Edit Chat' button")
    print("5. Try asking questions about the SOAP note")
    print("6. Try requesting modifications to the SOAP note")
    print("\nExample messages to try:")
    print("- 'Can you explain what this diagnosis means?'")
    print("- 'Add that the patient has diabetes'")
    print("- 'Change the treatment plan to include a crown'")
    print("- 'What are the next steps for this patient?'")