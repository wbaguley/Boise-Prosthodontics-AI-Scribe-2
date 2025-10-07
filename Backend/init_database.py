#!/usr/bin/env python3
"""
Database initialization script for Boise Prosthodontics AI Scribe
Run this to set up the database with initial providers
"""

import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import (
    create_provider, 
    get_all_providers,
    Base,
    engine
)

def init_database():
    """Initialize database with tables and default data"""
    
    print("🔧 Initializing database...")
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully")
    
    # Check if providers already exist
    existing_providers = get_all_providers(active_only=False)
    
    if existing_providers:
        print(f"\n📋 Found {len(existing_providers)} existing providers:")
        for provider in existing_providers:
            voice_status = "🎤" if provider['has_voice_profile'] else "❌"
            print(f"  - {provider['name']} {voice_status}")
        
        response = input("\nDo you want to add default providers anyway? (y/n): ")
        if response.lower() != 'y':
            print("Skipping default provider creation")
            return
    
    # Create default providers
    print("\n📝 Creating default providers...")
    
    default_providers = [
        {
            'name': 'Dr. Gurney',
            'specialty': 'Prosthodontics',
            'credentials': 'DDS, MS',
            'email': 'gurney@boiseprostho.com'
        },
        {
            'name': 'Dr. Smith',
            'specialty': 'Prosthodontics',
            'credentials': 'DMD',
            'email': 'smith@boiseprostho.com'
        }
    ]
    
    created_count = 0
    for provider_data in default_providers:
        try:
            result = create_provider(**provider_data)
            if result:
                print(f"  ✅ Created: {provider_data['name']}")
                created_count += 1
            else:
                print(f"  ⚠️  Already exists or failed: {provider_data['name']}")
        except Exception as e:
            print(f"  ❌ Error creating {provider_data['name']}: {e}")
    
    print(f"\n✅ Database initialization complete!")
    print(f"   Created {created_count} new providers")
    
    # Display final status
    print("\n📊 Current providers in database:")
    all_providers = get_all_providers(active_only=False)
    for provider in all_providers:
        status = "✓ Active" if provider['is_active'] else "✗ Inactive"
        voice = "🎤 Voice Profile" if provider['has_voice_profile'] else "❌ No Voice Profile"
        print(f"  • {provider['name']}")
        print(f"    {status} | {voice}")
        if provider['specialty']:
            print(f"    Specialty: {provider['specialty']}")
        if provider['credentials']:
            print(f"    Credentials: {provider['credentials']}")
        print()

def reset_database():
    """Drop all tables and recreate (CAUTION: deletes all data)"""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    response = input("Are you sure you want to continue? Type 'YES' to confirm: ")
    
    if response != 'YES':
        print("Aborted")
        return
    
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    print("✅ Tables dropped")
    
    print("Recreating tables...")
    Base.metadata.create_all(engine)
    print("✅ Tables recreated")
    
    print("\nDatabase has been reset. Run init_database() to add default data.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database management for AI Scribe')
    parser.add_argument(
        '--reset', 
        action='store_true', 
        help='Reset database (WARNING: deletes all data)'
    )
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    else:
        init_database()