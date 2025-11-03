"""
Database Migration - Add Dentrix Integration Columns
Adds sent_to_dentrix, dentrix_sent_at, dentrix_note_id, dentrix_patient_id to sessions table
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def migrate_add_dentrix_columns():
    """Add Dentrix integration columns to sessions table"""
    
    # Database path
    data_dir = Path("/app/data")
    db_path = data_dir / "sessions.db"
    
    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("No migration needed - database will be created with new schema")
        return True
    
    print(f"📦 Database found: {db_path}")
    print(f"🔧 Starting Dentrix columns migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        columns_to_add = []
        
        if 'sent_to_dentrix' not in columns:
            columns_to_add.append(('sent_to_dentrix', 'BOOLEAN DEFAULT 0'))
        
        if 'dentrix_sent_at' not in columns:
            columns_to_add.append(('dentrix_sent_at', 'DATETIME'))
        
        if 'dentrix_note_id' not in columns:
            columns_to_add.append(('dentrix_note_id', 'VARCHAR'))
        
        if 'dentrix_patient_id' not in columns:
            columns_to_add.append(('dentrix_patient_id', 'VARCHAR'))
        
        if not columns_to_add:
            print("✅ All Dentrix columns already exist - no migration needed")
            return True
        
        print(f"➕ Adding {len(columns_to_add)} columns:")
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            sql = f"ALTER TABLE sessions ADD COLUMN {column_name} {column_type}"
            print(f"   - {column_name} ({column_type})")
            cursor.execute(sql)
        
        conn.commit()
        print("✅ Dentrix columns migration completed successfully")
        
        # Verify columns were added
        cursor.execute("PRAGMA table_info(sessions)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        
        print("\n📊 Updated sessions table schema:")
        for col in ['sent_to_dentrix', 'dentrix_sent_at', 'dentrix_note_id', 'dentrix_patient_id']:
            if col in updated_columns:
                print(f"   ✅ {col}")
            else:
                print(f"   ❌ {col} - MISSING!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        if conn:
            conn.close()


def verify_dentrix_columns():
    """Verify Dentrix columns exist in database"""
    data_dir = Path("/app/data")
    db_path = data_dir / "sessions.db"
    
    if not db_path.exists():
        print("ℹ️  Database does not exist yet")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['sent_to_dentrix', 'dentrix_sent_at', 'dentrix_note_id', 'dentrix_patient_id']
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            print(f"❌ Missing Dentrix columns: {', '.join(missing)}")
            return False
        else:
            print("✅ All Dentrix columns present")
            return True
            
    except sqlite3.Error as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("DENTRIX DATABASE MIGRATION")
    print("="*70 + "\n")
    
    # Run migration
    success = migrate_add_dentrix_columns()
    
    if success:
        print("\n" + "="*70)
        print("VERIFICATION")
        print("="*70 + "\n")
        verify_dentrix_columns()
    
    print("\n" + "="*70 + "\n")
