"""
Test script for medical vocabulary integration with Whisper
"""

import logging
from medical_vocabulary import get_medical_vocabulary

logging.basicConfig(level=logging.INFO)

def test_medical_vocabulary():
    """Test medical vocabulary manager"""
    print("\n" + "="*70)
    print("🧪 TESTING MEDICAL VOCABULARY INTEGRATION")
    print("="*70)
    
    vocab = get_medical_vocabulary()
    
    # Test all specialties
    specialties = ["prosthodontics", "periodontics", "endodontics", "orthodontics", "oral_surgery", "general"]
    
    for specialty in specialties:
        print(f"\n📌 Testing {specialty.upper()}:")
        print("-" * 70)
        
        prompt = vocab.get_prompt_for_specialty(specialty)
        
        # Show first 150 characters
        preview = prompt[:150] + "..." if len(prompt) > 150 else prompt
        print(f"Prompt Preview: {preview}")
        
        # Validate prompt length
        validation = vocab.validate_prompt_length(prompt)
        print(f"✅ Valid: {validation['is_valid']}")
        print(f"📊 Estimated Tokens: {validation['estimated_tokens']} / {validation['max_tokens']}")
        print(f"📏 Prompt Length: {validation['prompt_length']} chars")
        
        if validation['warning']:
            print(f"⚠️ Warning: {validation['warning']}")
    
    # Test specialty info
    print("\n" + "="*70)
    print("📋 SPECIALTY VOCABULARY STATISTICS")
    print("="*70)
    
    for specialty in specialties:
        info = vocab.get_specialty_info(specialty)
        print(f"\n{specialty.upper()}:")
        print(f"  Total Terms: {info['total_terms']}")
        print(f"  Specialty-Specific: {info['specialty_specific_terms']}")
    
    # Test custom prompt
    print("\n" + "="*70)
    print("🔧 CUSTOM PROMPT TEST")
    print("="*70)
    
    custom_terms = ["Dr. Baguley", "Dr. Gurney", "BioHorizons", "Nobel Biocare", "Straumann"]
    custom_prompt = vocab.get_custom_prompt(custom_terms)
    print(f"\nAdded {len(custom_terms)} custom terms")
    print(f"Custom Prompt Preview: {custom_prompt[:200]}...")
    
    validation = vocab.validate_prompt_length(custom_prompt)
    print(f"\n✅ Valid: {validation['is_valid']}")
    print(f"📊 Estimated Tokens: {validation['estimated_tokens']} / {validation['max_tokens']}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_medical_vocabulary()
