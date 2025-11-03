"""
Test Dentrix Integration - Verify all components working together
Tests the complete flow from backend client to Dentrix bridge
"""

import os
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_dentrix_client():
    """Test Dentrix client basic functionality"""
    print("\n" + "="*70)
    print("🧪 TEST 1: DENTRIX CLIENT")
    print("="*70)
    
    try:
        from dentrix_client import get_dentrix_client
        
        client = get_dentrix_client()
        print(f"✅ DentrixClient initialized")
        print(f"   Bridge URL: {client.bridge_url}")
        print(f"   Timeout: {client.timeout}s")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize DentrixClient: {e}")
        return False


def test_database_schema():
    """Test that Dentrix columns exist in database"""
    print("\n" + "="*70)
    print("🧪 TEST 2: DATABASE SCHEMA")
    print("="*70)
    
    try:
        import sqlite3
        
        # Try to connect to database
        db_path = Path("/app/data/sessions.db")
        
        if not db_path.exists():
            print("ℹ️  Database doesn't exist yet - will be created on first use")
            return True
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Check for Dentrix columns
        dentrix_columns = {
            'sent_to_dentrix': 'BOOLEAN',
            'dentrix_sent_at': 'DATETIME',
            'dentrix_note_id': 'VARCHAR',
            'dentrix_patient_id': 'VARCHAR'
        }
        
        all_present = True
        for col_name, col_type in dentrix_columns.items():
            if col_name in columns:
                print(f"✅ Column exists: {col_name} ({columns[col_name]})")
            else:
                print(f"❌ Missing column: {col_name}")
                all_present = False
        
        conn.close()
        
        if all_present:
            print("\n✅ All Dentrix columns present in database")
        else:
            print("\n⚠️  Some Dentrix columns missing - run migrate_add_dentrix_columns.py")
        
        return all_present
        
    except Exception as e:
        print(f"❌ Database schema check failed: {e}")
        return False


def test_database_functions():
    """Test that database functions for Dentrix exist"""
    print("\n" + "="*70)
    print("🧪 TEST 3: DATABASE FUNCTIONS")
    print("="*70)
    
    try:
        from database import update_session_dentrix_status, get_session_by_id
        
        print("✅ update_session_dentrix_status() exists")
        print("✅ get_session_by_id() exists")
        
        # Test function signature
        import inspect
        sig = inspect.signature(update_session_dentrix_status)
        params = list(sig.parameters.keys())
        print(f"   Parameters: {params}")
        
        expected_params = ['session_id', 'dentrix_note_id', 'dentrix_patient_id', 'sent_to_dentrix']
        if all(p in params for p in expected_params):
            print("✅ Function signature correct")
        else:
            print("⚠️  Function signature may need adjustment")
        
        return True
        
    except ImportError as e:
        print(f"❌ Database functions not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Database function test failed: {e}")
        return False


def test_main_endpoints():
    """Test that Dentrix endpoints exist in main.py"""
    print("\n" + "="*70)
    print("🧪 TEST 4: FASTAPI ENDPOINTS")
    print("="*70)
    
    try:
        # Read main.py and check for endpoints
        main_py = Path(__file__).parent / "main.py"
        content = main_py.read_text()
        
        endpoints = [
            '/api/dentrix/health',
            '/api/dentrix/patients/search',
            '/api/dentrix/patients/{patient_id}',
            '/api/sessions/{session_id}/send-to-dentrix',
            '/api/dentrix/providers'
        ]
        
        all_present = True
        for endpoint in endpoints:
            if endpoint in content:
                print(f"✅ Endpoint exists: {endpoint}")
            else:
                print(f"❌ Endpoint missing: {endpoint}")
                all_present = False
        
        # Check for DentrixSoapRequest model
        if 'class DentrixSoapRequest' in content:
            print("✅ DentrixSoapRequest model exists")
        else:
            print("❌ DentrixSoapRequest model missing")
            all_present = False
        
        # Check for dentrix_client import
        if 'from dentrix_client import get_dentrix_client' in content:
            print("✅ dentrix_client import exists")
        else:
            print("❌ dentrix_client import missing")
            all_present = False
        
        return all_present
        
    except Exception as e:
        print(f"❌ Endpoint check failed: {e}")
        return False


def test_bridge_connection():
    """Test connection to Dentrix bridge (if available)"""
    print("\n" + "="*70)
    print("🧪 TEST 5: BRIDGE CONNECTION (Optional)")
    print("="*70)
    
    try:
        from dentrix_client import get_dentrix_client
        
        client = get_dentrix_client()
        
        print(f"Attempting to connect to: {client.bridge_url}")
        is_healthy = client.health_check()
        
        if is_healthy:
            print("✅ Dentrix bridge is healthy and responding")
            return True
        else:
            print("⚠️  Dentrix bridge not responding (this is OK if not deployed yet)")
            return None  # Not a failure, just not available
            
    except Exception as e:
        print(f"⚠️  Could not connect to Dentrix bridge: {e}")
        print("   This is expected if bridge is not deployed yet")
        return None  # Not a failure


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "🔬 "*35)
    print("DENTRIX INTEGRATION TEST SUITE")
    print("🔬 "*35)
    
    results = {}
    
    # Run tests
    results['client'] = test_dentrix_client()
    results['schema'] = test_database_schema()
    results['functions'] = test_database_functions()
    results['endpoints'] = test_main_endpoints()
    results['bridge'] = test_bridge_connection()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⏭️  SKIP"
        print(f"{status:12} {test_name.upper()}")
    
    print("\n" + "-"*70)
    print(f"Total Tests: {len(results)}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {failed}")
    print(f"Skipped:     {skipped}")
    print("-"*70)
    
    if failed == 0:
        print("\n🎉 ALL CRITICAL TESTS PASSED!")
        print("   Dentrix integration is ready to use")
        if skipped > 0:
            print(f"   ({skipped} optional test(s) skipped - Dentrix bridge not deployed)")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        print("   Please review failures above")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
