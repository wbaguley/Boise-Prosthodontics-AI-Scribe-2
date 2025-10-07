#!/bin/bash

echo "Testing SOAP Chat Feature..."

# Test with properly formatted JSON
curl -X POST http://localhost:8000/api/edit-soap-chat \
  -H "Content-Type: application/json" \
  -d '{
    "original_soap": "SUBJECTIVE:\n- Chief Complaint: Tooth pain\n\nOBJECTIVE:\n- Clinical findings\n\nASSESSMENT:\n- Diagnosis needed\n\nPLAN:\n- Treatment plan",
    "transcript": "Doctor: Hello, what brings you in today? Patient: I have tooth pain.",
    "user_message": "Add that the patient has diabetes type 2",
    "chat_history": []
  }' | jq '.'

echo -e "\n\nTesting question vs modification detection..."

# Test question (should not modify SOAP)
curl -X POST http://localhost:8000/api/edit-soap-chat \
  -H "Content-Type: application/json" \
  -d '{
    "original_soap": "SUBJECTIVE:\n- Chief Complaint: Tooth pain",
    "transcript": "Doctor: Hello",
    "user_message": "What does this diagnosis mean?",
    "chat_history": []
  }' | jq '.soap_modified'