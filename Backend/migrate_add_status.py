#!/usr/bin/env python3
"""
Migration script to add status column to sessions table
"""
import sqlite3
import os

def migrate_database():
    """Add status column to existing sessions table"""
    # The application uses /app/data/sessions.db
    db_path = '/app/data/sessions.db'
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Migrating database at {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if status column already exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' in columns:
            print("✅ Status column already exists, no migration needed")
            conn.close()
            return True
        
        # Add status column with default value 'completed' for existing sessions
        print("Adding status column to sessions table...")
        cursor.execute("""
            ALTER TABLE sessions 
            ADD COLUMN status TEXT DEFAULT 'completed'
        """)
        
        # Update all existing sessions to have 'completed' status
        cursor.execute("""
            UPDATE sessions 
            SET status = 'completed' 
            WHERE status IS NULL
        """)
        
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' in columns:
            cursor.execute("SELECT COUNT(*) FROM sessions")
            count = cursor.fetchone()[0]
            print(f"✅ Migration successful!")
            print(f"   - Added 'status' column to sessions table")
            print(f"   - Updated {count} existing sessions to 'completed' status")
            conn.close()
            return True
        else:
            print("❌ Migration failed - status column not found after adding")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    exit(0 if success else 1)
