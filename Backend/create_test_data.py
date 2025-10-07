from database import save_session, create_provider
from datetime import datetime, timedelta
import uuid

def create_test_data():
    """Create test providers and sessions"""
    
    # Create test providers
    providers = [
        {"name": "Dr. John Smith", "specialty": "Prosthodontics", "credentials": "DDS, MS"},
        {"name": "Dr. Sarah Wilson", "specialty": "General Dentistry", "credentials": "DDS"},
        {"name": "Dr. Michael Chen", "specialty": "Oral Surgery", "credentials": "DDS, MD"}
    ]
    
    print("Creating test providers...")
    for provider in providers:
        try:
            create_provider(provider["name"], provider["specialty"], provider["credentials"])
            print(f"✅ Created provider: {provider['name']}")
        except Exception as e:
            print(f"⚠️ Provider {provider['name']} may already exist: {e}")
    
    # Create test sessions
    test_sessions = [
        {
            "doctor": "Dr. John Smith",
            "transcript": """Patient came in for crown consultation. Chief complaint is broken molar on upper right. 
            
            Dr. Smith: Good morning! I see you're here about a broken tooth. Can you tell me what happened?
            
            Patient: Yes, I was eating some nuts yesterday and heard a crack. Now there's a sharp piece and it hurts when I bite down.
            
            Dr. Smith: Let me take a look. I can see the fracture line on your upper right first molar. The good news is that the root looks healthy. We'll need to do a crown to restore this tooth properly.
            
            Patient: How long will that take?
            
            Dr. Smith: We can do it in two visits. Today we'll prepare the tooth and take impressions, then in two weeks you'll come back for the permanent crown placement.
            
            Patient: Sounds good. Will I be able to eat normally?
            
            Dr. Smith: We'll give you a temporary crown today, so you should avoid sticky foods and chew on the other side. The permanent crown will restore full function.""",
            
            "soap_note": """SUBJECTIVE:
- Chief Complaint: Broken molar on upper right, occurred yesterday while eating nuts
- Pain with biting and sharp edges present
- Patient reports hearing a "crack" sound during incident
- No prior issues with this tooth

OBJECTIVE:
- Clinical Examination: Fracture visible on tooth #3 (upper right first molar)
- Fracture line extends from mesial cusp to central groove
- Root appears healthy on clinical examination
- No signs of pulpal involvement
- Patient demonstrates normal occlusion otherwise

ASSESSMENT:
- Fractured crown on tooth #3
- Tooth structure sufficient for crown restoration
- No apparent endodontic involvement

PLAN:
- Crown preparation and temporary crown placement today
- Impressions for permanent crown
- Permanent crown cementation in 2 weeks
- Post-op instructions provided for temporary crown care
- Follow-up appointment scheduled""",
            
            "template": "treatment_consultation",
            "timestamp": datetime.now() - timedelta(days=2)
        },
        
        {
            "doctor": "Dr. Sarah Wilson", 
            "transcript": """New patient consultation for comprehensive exam and cleaning.
            
            Dr. Wilson: Welcome to our practice! This is your first visit with us, so we'll do a comprehensive examination and cleaning today.
            
            Patient: Thank you. I haven't been to the dentist in about 2 years, so I'm a bit nervous.
            
            Dr. Wilson: That's completely normal. We'll take good care of you. Can you tell me about any concerns you have?
            
            Patient: My gums bleed when I brush, and I think I might have a cavity on the left side.
            
            Dr. Wilson: Let's take a look. I can see some plaque buildup and your gums are showing signs of gingivitis. The good news is this is very treatable with proper care.
            
            Patient: What about the cavity?
            
            Dr. Wilson: I see a small area of decay on your lower left molar. It's not too deep, so we can restore it with a simple filling at your next visit.""",
            
            "soap_note": """SUBJECTIVE:
- New patient, last dental visit 2 years ago
- Chief complaints: Bleeding gums, possible cavity left side
- Reports anxiety about dental treatment
- No current pain or acute symptoms

OBJECTIVE:
- Comprehensive oral examination completed
- Generalized plaque and calculus accumulation
- Gingivitis present, especially posterior regions
- Small occlusal caries on tooth #19 (lower left first molar)
- No signs of periodontitis or advanced disease

ASSESSMENT:
- Gingivitis due to plaque accumulation
- Dental caries tooth #19, Class I occlusal
- Overall good oral health with opportunity for improvement

PLAN:
- Prophylaxis and oral hygiene instruction completed today
- Schedule composite restoration tooth #19
- Recommend improved home care routine
- 6-month recall examination and cleaning
- Patient education materials provided""",
            
            "template": "new_patient",
            "timestamp": datetime.now() - timedelta(days=5)
        },
        
        {
            "doctor": "Dr. Michael Chen",
            "transcript": """Patient referred for wisdom tooth evaluation and possible extraction.
            
            Dr. Chen: I've reviewed your X-rays from Dr. Wilson's office. You're here about your wisdom teeth, is that right?
            
            Patient: Yes, the bottom ones have been bothering me. There's not enough room and food keeps getting stuck.
            
            Dr. Chen: I can see that. Your lower wisdom teeth are partially erupted and impacted. This is causing the food trap and can lead to infection if we don't address it.
            
            Patient: Do they both need to come out?
            
            Dr. Chen: I'd recommend removing both lower wisdom teeth. The upper ones look fine for now, but we'll keep monitoring them.
            
            Patient: How complicated is the procedure?
            
            Dr. Chen: The left one is straightforward, but the right one is a bit more involved due to its position. We can do them both in one visit under IV sedation if you prefer.""",
            
            "soap_note": """SUBJECTIVE:
- Referred by Dr. Wilson for wisdom tooth evaluation
- Chief complaint: Food impaction and discomfort with lower wisdom teeth
- Reports difficulty cleaning area properly
- No acute pain or swelling currently

OBJECTIVE:
- Clinical and radiographic examination completed
- Teeth #17, #32 partially erupted and mesially impacted
- Evidence of plaque accumulation and mild pericoronitis
- Adequate bone support for extraction
- No signs of nerve involvement

ASSESSMENT:
- Impacted wisdom teeth #17, #32 with chronic pericoronitis
- Risk for recurrent infection and caries if retained
- Surgical extraction recommended

PLAN:
- Surgical extraction of teeth #17, #32 recommended
- IV sedation offered for patient comfort
- Pre-operative instructions and consent obtained
- Post-operative care instructions provided
- Schedule surgical appointment
- Continue monitoring teeth #1, #16""",
            
            "template": "treatment_consultation", 
            "timestamp": datetime.now() - timedelta(days=1)
        }
    ]
    
    print("\nCreating test sessions...")
    for i, session_data in enumerate(test_sessions):
        session_id = f"test-session-{i+1}-{uuid.uuid4().hex[:8]}"
        
        success = save_session(
            session_id=session_id,
            doctor=session_data["doctor"],
            transcript=session_data["transcript"],
            soap_note=session_data["soap_note"],
            template=session_data["template"],
            provider_id=None
        )
        
        if success:
            print(f"✅ Created session: {session_id} ({session_data['doctor']})")
        else:
            print(f"❌ Failed to create session: {session_id}")
    
    print("\n🎉 Test data creation completed!")

if __name__ == "__main__":
    create_test_data()