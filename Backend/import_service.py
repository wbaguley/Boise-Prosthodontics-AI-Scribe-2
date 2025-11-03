"""
Import Service for Boise Prosthodontics AI Scribe
Provides functionality to import data from various formats (ZIP, CSV, JSON)
"""

import io
import json
import csv
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List
import logging

from database import create_provider, get_provider_by_name, update_provider_voice_profile


class ImportService:
    """Service for importing data from various formats"""
    
    def __init__(self):
        """Initialize import service"""
        self.voice_profiles_dir = Path("/app/voice_profiles")
        self.soap_templates_dir = Path("/app/soap_templates")
        self.voice_profiles_dir.mkdir(exist_ok=True)
        self.soap_templates_dir.mkdir(exist_ok=True)
        logging.info("✅ Import service initialized")
    
    def import_voice_profile(self, provider_name: str, zip_bytes: bytes) -> bool:
        """
        Extract ZIP file containing voice profile
        
        Args:
            provider_name: Provider name
            zip_bytes: ZIP file content
            
        Returns:
            bool: Success status
        """
        try:
            # Sanitize provider name for directory
            safe_name = provider_name.lower().replace(' ', '_')
            profile_dir = self.voice_profiles_dir / safe_name
            
            # Create directory
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                # Validate required files
                file_list = zip_file.namelist()
                
                if 'profile.pkl' not in file_list:
                    raise ValueError("ZIP file must contain profile.pkl")
                
                # Extract all files
                zip_file.extractall(profile_dir)
                
                # Verify metadata
                metadata_file = profile_dir / 'metadata.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        logging.info(f"Voice profile metadata: {metadata}")
            
            # Update provider record in database
            provider = get_provider_by_name(provider_name)
            if provider:
                update_provider_voice_profile(
                    provider['id'],
                    has_profile=True,
                    profile_path=str(profile_dir)
                )
                logging.info(f"✅ Updated provider {provider_name} with voice profile")
            else:
                logging.warning(f"Provider {provider_name} not found in database")
            
            logging.info(f"✅ Imported voice profile for {provider_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error importing voice profile for {provider_name}: {e}")
            # Clean up on error
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
            raise
    
    def import_providers_csv(self, csv_data: str) -> Dict[str, any]:
        """
        Parse CSV with provider data and create providers
        
        Args:
            csv_data: CSV file content
            
        Returns:
            dict: Import results with created count, failed count, and errors
        """
        try:
            created = 0
            failed = 0
            errors = []
            
            # Parse CSV
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            # Expected columns
            required_columns = ['name']
            optional_columns = ['specialty', 'credentials', 'email']
            
            # Validate headers
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")
            
            if 'name' not in reader.fieldnames:
                raise ValueError("CSV must have 'name' column")
            
            # Process rows
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                try:
                    name = row.get('name', '').strip()
                    if not name:
                        errors.append(f"Row {row_num}: Name is required")
                        failed += 1
                        continue
                    
                    # Check if provider already exists
                    existing = get_provider_by_name(name)
                    if existing:
                        errors.append(f"Row {row_num}: Provider '{name}' already exists")
                        failed += 1
                        continue
                    
                    # Create provider
                    result = create_provider(
                        name=name,
                        specialty=row.get('specialty', '').strip() or None,
                        credentials=row.get('credentials', '').strip() or None,
                        email=row.get('email', '').strip() or None
                    )
                    
                    if 'error' in result:
                        errors.append(f"Row {row_num}: {result['error']}")
                        failed += 1
                    else:
                        created += 1
                        logging.info(f"✅ Created provider: {name}")
                        
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    failed += 1
            
            result = {
                'created': created,
                'failed': failed,
                'errors': errors,
                'total_rows': created + failed
            }
            
            logging.info(f"✅ Provider import complete: {created} created, {failed} failed")
            return result
            
        except Exception as e:
            logging.error(f"Error importing providers CSV: {e}")
            raise
    
    def import_soap_templates(self, json_data: dict) -> bool:
        """
        Import custom SOAP note templates
        
        Args:
            json_data: JSON template data
            
        Returns:
            bool: Success status
        """
        try:
            # Validate JSON structure
            if not isinstance(json_data, dict):
                raise ValueError("Template data must be a JSON object")
            
            # Check if it's a single template or multiple templates
            if 'templates' in json_data:
                # Multiple templates
                templates = json_data['templates']
                if not isinstance(templates, list):
                    raise ValueError("'templates' must be a list")
            else:
                # Single template - wrap in list
                templates = [json_data]
            
            imported_count = 0
            
            for template in templates:
                # Validate required fields
                if 'id' not in template:
                    raise ValueError("Each template must have an 'id' field")
                
                if 'name' not in template:
                    raise ValueError("Each template must have a 'name' field")
                
                if 'sections' not in template:
                    raise ValueError("Each template must have a 'sections' field")
                
                # Sanitize template ID
                template_id = template['id'].lower().replace(' ', '_')
                template_file = self.soap_templates_dir / f"{template_id}.json"
                
                # Save template
                with open(template_file, 'w') as f:
                    json.dump(template, f, indent=2)
                
                imported_count += 1
                logging.info(f"✅ Imported template: {template['name']} ({template_id})")
            
            logging.info(f"✅ Imported {imported_count} SOAP template(s)")
            return True
            
        except Exception as e:
            logging.error(f"Error importing SOAP templates: {e}")
            raise
    
    def validate_voice_profile_zip(self, zip_bytes: bytes) -> Dict[str, any]:
        """
        Validate voice profile ZIP file structure
        
        Args:
            zip_bytes: ZIP file content
            
        Returns:
            dict: Validation results
        """
        try:
            result = {
                'valid': True,
                'has_profile_pkl': False,
                'has_metadata': False,
                'sample_count': 0,
                'errors': []
            }
            
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Check for profile.pkl
                if 'profile.pkl' in file_list:
                    result['has_profile_pkl'] = True
                else:
                    result['valid'] = False
                    result['errors'].append("Missing required file: profile.pkl")
                
                # Check for metadata.json
                if 'metadata.json' in file_list:
                    result['has_metadata'] = True
                    try:
                        metadata_content = zip_file.read('metadata.json')
                        json.loads(metadata_content)
                    except json.JSONDecodeError:
                        result['errors'].append("metadata.json is not valid JSON")
                
                # Count sample files
                sample_files = [f for f in file_list if f.startswith('samples/') and f.endswith('.wav')]
                result['sample_count'] = len(sample_files)
            
            return result
            
        except zipfile.BadZipFile:
            return {
                'valid': False,
                'errors': ['Invalid ZIP file']
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)]
            }


# Global import service instance
import_service = ImportService()
