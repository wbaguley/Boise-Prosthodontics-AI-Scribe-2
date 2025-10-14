# Installation Instructions for Timezone Functionality

## Overview

The AI Scribe system has been enhanced with comprehensive timezone support and improved SOAP note generation that prevents generic responses.

## Changes Made

### 1. SOAP Note Generation Improvements
- **Enhanced AI instruction enforcement**: The system now validates SOAP notes to prevent generic phrases like "see transcript", "as discussed", etc.
- **Multi-attempt generation**: Up to 3 attempts with stricter prompts if generic responses are detected
- **Intelligent fallback**: If AI generation fails, an enhanced fallback system extracts specific details from the transcript
- **Strict validation**: Automatic rejection of responses containing forbidden phrases

### 2. Timezone Configuration System
- **Database schema**: Added `SystemConfig` table for system-wide settings
- **Timezone utilities**: Comprehensive timezone handling with pytz integration
- **API endpoints**: Full REST API for timezone and system configuration management
- **Frontend interface**: User-friendly timezone selection and system configuration UI

### 3. Updated Components

#### Backend Files Modified/Added:
- `main.py` - Enhanced SOAP generation and timezone API endpoints
- `database.py` - Added SystemConfig table and CRUD operations  
- `timezone_utils.py` - **NEW** - Timezone handling utilities
- `requirements.txt` - Added pytz dependency

#### Frontend Files Modified/Added:
- `src/components/SystemConfig.js` - **NEW** - System configuration interface
- `src/App.js` - Added SystemConfig route
- `src/components/Dashboard.js` - Added System Config button

## Installation Steps

### 1. Install Python Dependencies
```bash
cd Backend
pip install pytz==2023.3
```

### 2. Database Migration
The system will automatically create the new `system_config` table and initialize default settings on startup.

Default timezone settings:
- **Timezone**: America/Denver (Mountain Time)
- **Date Format**: %Y-%m-%d
- **Time Format**: %H:%M:%S
- **DateTime Format**: %Y-%m-%d %H:%M:%S

### 3. Frontend Dependencies
No additional frontend dependencies required - uses existing React setup.

### 4. Configuration Access

#### Via Web Interface:
1. Open the AI Scribe dashboard
2. Click "🕒 System Config" button
3. Select desired timezone from dropdown
4. Changes apply immediately

#### Via API:
```bash
# Get current timezone
curl http://localhost:8000/api/timezone/current

# Set timezone  
curl -X POST http://localhost:8000/api/timezone \
  -H "Content-Type: application/json" \
  -d '{"timezone": "America/New_York"}'

# Get all system configs
curl http://localhost:8000/api/system-config

# Set configuration
curl -X POST http://localhost:8000/api/system-config \
  -H "Content-Type: application/json" \
  -d '{"key": "clinic_name", "value": "My Clinic", "description": "Clinic name"}'
```

## Available Timezones

The system supports these common US timezones:
- America/New_York (Eastern Time)
- America/Chicago (Central Time)  
- America/Denver (Mountain Time)
- America/Phoenix (Arizona Time - no DST)
- America/Los_Angeles (Pacific Time)
- America/Anchorage (Alaska Time)
- Pacific/Honolulu (Hawaii Time)
- UTC (Universal Time)

## Testing the Setup

### 1. Backend Test
```bash
cd Backend
python -c "
import timezone_utils
import pytz
print('✅ Timezone utilities working')
print(f'Current system time: {timezone_utils.now_in_system_timezone()}')
print(f'Available timezones: {len(timezone_utils.get_available_timezones())}')
"
```

### 2. API Test
```bash
# Start the backend
python main.py

# In another terminal, test the API
curl http://localhost:8000/api/timezone/current
```

### 3. SOAP Note Test
Create a test recording session and verify that:
- SOAP notes contain specific details from the transcript
- No generic phrases like "see transcript" appear
- Timestamps use the configured timezone

## Benefits

### For SOAP Note Quality:
- **No more generic responses**: AI is forced to extract and write specific details
- **Professional narrative format**: Notes read like actual doctor documentation  
- **Compliance with templates**: AI follows the exact template structure and instructions
- **Fallback protection**: Even if AI fails, fallback system creates meaningful notes

### For Timezone Management:
- **Accurate timestamps**: All times displayed in the clinic's timezone
- **Consistent documentation**: SOAP notes and emails use local time
- **Easy configuration**: Change timezone through web interface
- **Multi-timezone support**: System handles DST and timezone conversions automatically

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'pytz'`:
```bash
pip install pytz==2023.3
```

### Database Errors
If system config table doesn't exist:
```bash
# Delete the database file to force recreation
rm Backend/data/sessions.db
# Restart the backend - it will recreate with new schema
```

### SOAP Note Issues
If SOAP notes are still generic:
1. Check that AI instructions are properly loaded in templates
2. Verify Ollama is running and responding
3. Check logs for validation errors

### Timezone Display Issues
If times are showing in UTC:
1. Verify timezone is set via API or web interface
2. Check that pytz is installed
3. Restart backend after timezone changes

## Future Enhancements

The timezone system is designed for future expansion:
- Multiple user timezone preferences
- Automatic timezone detection
- International timezone support
- Appointment scheduling with timezone awareness
- Email delivery timing optimization