#!/usr/bin/env python3
"""
Initialize data directory structure for proper persistence
"""

import os
from pathlib import Path
import json

def init_data_directories():
    """Initialize all necessary data directories and files"""
    
    # Create data directories
    data_dir = Path("/app/data")
    data_dir.mkdir(exist_ok=True)
    
    # Templates directory (already mapped as volume)
    templates_dir = Path("/app/soap_templates") 
    templates_dir.mkdir(exist_ok=True)
    
    # Voice profiles directory (already mapped as volume)
    voice_profiles_dir = Path("/app/voice_profiles")
    voice_profiles_dir.mkdir(exist_ok=True)
    
    # Models directory (already mapped as volume)
    models_dir = Path("/app/models")
    models_dir.mkdir(exist_ok=True)
    
    # Logs directory (already mapped as volume)  
    logs_dir = Path("/app/logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Initialize knowledge articles file if it doesn't exist
    knowledge_file = data_dir / "knowledge_articles.json"
    if not knowledge_file.exists():
        with open(knowledge_file, 'w') as f:
            json.dump([], f)
    
    # Create session database directory marker (database.py will create the actual file)
    db_marker = data_dir / ".db_initialized"
    if not db_marker.exists():
        db_marker.touch()
    
    print("Data directory structure initialized successfully:")
    print(f"  - Data directory: {data_dir}")
    print(f"  - Templates directory: {templates_dir}")
    print(f"  - Voice profiles directory: {voice_profiles_dir}")
    print(f"  - Models directory: {models_dir}")
    print(f"  - Logs directory: {logs_dir}")
    print(f"  - Knowledge articles: {knowledge_file}")

if __name__ == "__main__":
    init_data_directories()