# Dentrix Integration Guide

Complete guide for integrating Boise Prosthodontics AI Scribe with Dentrix practice management system.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cloud Environment (AWS/Azure)                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Boise Prosthodontics AI Scribe Backend           │  │
│  │                                                            │  │
│  │  - Audio transcription (Whisper)                          │  │
│  │  - SOAP note generation (Ollama)                          │  │
│  │  - Session management                                     │  │
│  │  - DentrixClient (HTTP client)                           │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
└─────────────────────────┼────────────────────────────────────────┘
                          │ HTTPS REST API
                          │ (over internet)
                          │
┌─────────────────────────┼────────────────────────────────────────┐
│                         │  On-Premise Environment                │
│                         │  (Dental Office Network)               │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │            Dentrix Bridge Service                         │  │
│  │            (FastAPI on Windows Server)                    │  │
│  │                                                            │  │
│  │  - REST API endpoints (port 8080)                         │  │
│  │  - SQL Server connectivity (ODBC)                         │  │
│  │  - SOAP note parsing and posting                          │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │ SQL Connection                        │
│                         │ (TCP 1433)                            │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │         Dentrix SQL Server Database                       │  │
│  │                                                            │  │
│  │  - Patient demographics                                   │  │
│  │  - Clinical notes                                         │  │
│  │  - Appointments                                           │  │
│  │  - Insurance information                                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### Cloud Backend Requirements
- Python 3.11+
- FastAPI backend running
- Network access to on-premise Dentrix bridge
- Environment variable: `DENTRIX_BRIDGE_URL`

### On-Premise Requirements
- Windows Server (2012 R2 or higher)
- Python 3.11+
- Microsoft ODBC Driver 18 for SQL Server
- Network access to Dentrix SQL Server
- Dentrix DDP (Dentrix Developer Program) enabled

## 🚀 Installation

### Part 1: Deploy Dentrix Bridge (On-Premise)

1. **Copy Dentrix Bridge Files to On-Premise Server**
   ```powershell
   # Copy dentrix_bridge folder to Windows Server
   # Recommended location: C:\DentrixBridge\
   ```

2. **Install Python Dependencies**
   ```powershell
   cd C:\DentrixBridge
   python -m pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   ```powershell
   # Copy .env.example to .env
   Copy-Item .env.example .env
   
   # Edit .env with your Dentrix SQL Server details
   notepad .env
   ```

4. **Configure .env File**
   ```ini
   # Dentrix SQL Server Connection
   DENTRIX_SQL_SERVER=localhost
   DENTRIX_DATABASE=Dentrix
   DENTRIX_USE_WINDOWS_AUTH=true
   # Or use SQL authentication:
   # DENTRIX_USERNAME=sa
   # DENTRIX_PASSWORD=your_password
   
   # Bridge Service Configuration
   DENTRIX_BRIDGE_PORT=8080
   ALLOWED_ORIGINS=https://your-ai-scribe-domain.com
   ```

5. **Test Dentrix Bridge**
   ```powershell
   python main.py
   
   # Bridge should start on http://localhost:8080
   # Test health: http://localhost:8080/health
   ```

6. **Optional: Install as Windows Service**
   ```powershell
   # Using NSSM (Non-Sucking Service Manager)
   nssm install DentrixBridge "C:\Python311\python.exe" "C:\DentrixBridge\main.py"
   nssm start DentrixBridge
   ```

### Part 2: Configure Cloud Backend

1. **Set Environment Variable**
   ```bash
   # Add to Backend/.env or environment
   DENTRIX_BRIDGE_URL=http://your-office-ip:8080
   
   # If using reverse proxy with domain:
   DENTRIX_BRIDGE_URL=https://dentrix.your-office.com
   ```

2. **Run Database Migration**
   ```bash
   cd Backend
   python migrate_add_dentrix_columns.py
   ```

3. **Restart Backend**
   ```bash
   # If using Docker:
   docker-compose restart backend
   
   # If running directly:
   python main.py
   ```

## 🔌 API Endpoints

### Cloud Backend Endpoints

#### Check Dentrix Bridge Health
```http
GET /api/dentrix/health
```

**Response:**
```json
{
  "success": true,
  "dentrix_available": true,
  "bridge_url": "http://your-office:8080",
  "message": "Dentrix bridge is healthy"
}
```

#### Search Patients
```http
GET /api/dentrix/patients/search?query=Smith
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "patients": [
    {
      "patient_id": 12345,
      "name": "Smith, John",
      "dob": "1980-05-15",
      "chart_number": "JS12345",
      "phone": "208-555-1234"
    }
  ]
}
```

#### Get Patient Details
```http
GET /api/dentrix/patients/12345
```

**Response:**
```json
{
  "success": true,
  "patient": {
    "patient_id": 12345,
    "first_name": "John",
    "last_name": "Smith",
    "dob": "1980-05-15",
    "chart_number": "JS12345",
    "insurance": {
      "primary_carrier": "Delta Dental",
      "subscriber_id": "123456789"
    }
  }
}
```

#### Send SOAP Note to Dentrix
```http
POST /api/sessions/{session_id}/send-to-dentrix
Content-Type: application/json

{
  "patient_id": 12345,
  "provider_id": 1,
  "note_type": "SOAP",
  "note_date": "2024-01-15"
}
```

**Response:**
```json
{
  "success": true,
  "dentrix_note_id": 98765,
  "message": "SOAP note successfully sent to Dentrix",
  "timestamp": "2024-01-15T14:30:00"
}
```

#### Get Dentrix Providers
```http
GET /api/dentrix/providers
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "providers": [
    {
      "provider_id": 1,
      "name": "Dr. Baguley",
      "credentials": "DDS",
      "specialty": "Prosthodontics",
      "npi": "1234567890"
    }
  ]
}
```

### Dentrix Bridge Endpoints

See [dentrix_bridge/README.md](../dentrix_bridge/README.md) for complete bridge API documentation.

## 📊 Database Schema

### New Session Columns

The migration adds these columns to the `sessions` table:

| Column Name | Type | Description |
|------------|------|-------------|
| `sent_to_dentrix` | BOOLEAN | Whether SOAP note has been sent to Dentrix |
| `dentrix_sent_at` | DATETIME | Timestamp when sent to Dentrix |
| `dentrix_note_id` | VARCHAR | Dentrix clinical note ID |
| `dentrix_patient_id` | VARCHAR | Dentrix patient ID |

## 🔄 Typical Workflow

### Recording Session with Dentrix Integration

1. **Start Recording Session**
   - Provider records patient visit
   - AI Scribe transcribes and generates SOAP note

2. **Search for Patient in Dentrix**
   ```javascript
   // Frontend calls search endpoint
   const response = await fetch('/api/dentrix/patients/search?query=Smith');
   const { patients } = await response.json();
   ```

3. **Select Patient**
   - User selects correct patient from search results
   - Get full patient details if needed

4. **Send SOAP Note to Dentrix**
   ```javascript
   const response = await fetch(`/api/sessions/${sessionId}/send-to-dentrix`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       patient_id: selectedPatient.patient_id,
       provider_id: 1,
       note_type: 'SOAP'
     })
   });
   ```

5. **Verify in Dentrix**
   - SOAP note appears in patient's clinical notes
   - Session marked as `sent_to_dentrix = true`

## 🔐 Security Considerations

### Network Security

1. **Firewall Configuration**
   - Open port 8080 on on-premise server for bridge
   - Use VPN or secure tunnel for cloud-to-premise connection
   - Consider reverse proxy with SSL/TLS

2. **Authentication**
   - Bridge currently uses CORS for origin validation
   - Consider adding API key authentication
   - Use Windows Authentication for SQL Server (recommended)

3. **HIPAA Compliance**
   - All PHI stays on-premise in Dentrix database
   - Bridge only acts as secure API gateway
   - No PHI stored in bridge service logs
   - Enable HTTPS for all connections

### Recommended Network Setup

```
Cloud AI Scribe
      ↓ HTTPS (TLS 1.2+)
   VPN Tunnel
      ↓
Office Firewall (port 8080)
      ↓
Dentrix Bridge (Windows Server)
      ↓ SQL Connection (encrypted)
Dentrix SQL Server
```

## 🧪 Testing

### Test Dentrix Client (Backend)
```bash
cd Backend
python dentrix_client.py

# Should show:
# 🧪 TESTING DENTRIX CLIENT
# Health Status: ✅ Healthy
```

### Test Dentrix Bridge (On-Premise)
```powershell
cd C:\DentrixBridge
python main.py

# In another terminal:
Invoke-WebRequest -Uri http://localhost:8080/health

# Should return:
# { "status": "healthy", "dentrix_connection": true }
```

### Test Full Integration
```bash
# From Backend directory
cd Backend
python -c "
from dentrix_client import get_dentrix_client

client = get_dentrix_client()

# Test health
print('Testing health...')
healthy = client.health_check()
print(f'Healthy: {healthy}')

# Test patient search
print('\\nTesting patient search...')
patients = client.search_patients('Test')
print(f'Found {len(patients)} patients')

# Test providers
print('\\nTesting providers...')
providers = client.get_providers()
print(f'Found {len(providers)} providers')
"
```

## 🐛 Troubleshooting

### Bridge Connection Issues

**Problem:** Backend cannot connect to Dentrix bridge

**Solutions:**
1. Verify bridge is running: `http://your-office:8080/health`
2. Check firewall allows port 8080
3. Verify `DENTRIX_BRIDGE_URL` environment variable
4. Test from backend server: `curl http://your-office:8080/health`

### SQL Server Connection Issues

**Problem:** Bridge cannot connect to Dentrix SQL Server

**Solutions:**
1. Verify SQL Server is running
2. Check ODBC Driver 18 is installed
3. Test connection string:
   ```powershell
   sqlcmd -S localhost -d Dentrix -E
   ```
4. Verify Dentrix DDP is enabled
5. Check SQL Server allows remote connections

### SOAP Note Posting Issues

**Problem:** SOAP notes fail to post to Dentrix

**Solutions:**
1. Verify patient ID exists in Dentrix
2. Check provider ID is valid
3. Review SOAP note format (must have S/O/A/P sections)
4. Check Dentrix clinical notes table permissions
5. Review bridge logs for SQL errors

### Migration Issues

**Problem:** Database migration fails

**Solutions:**
1. Backup database before migration
2. Verify database file exists at `/app/data/sessions.db`
3. Check file permissions
4. Run migration script directly:
   ```bash
   python migrate_add_dentrix_columns.py
   ```

## 📝 Logging

### Backend Logs
```bash
# View Dentrix integration logs
tail -f logs/scribe_logs.txt | grep Dentrix

# Common log messages:
# ✅ SOAP note created in Dentrix: Note ID 98765
# 🔍 Searching Dentrix patients: 'Smith'
# ❌ Dentrix bridge timeout: http://office:8080/api/patients/search
```

### Bridge Logs
```powershell
# View bridge console output
# Logs show all API requests and SQL queries
```

## 🔄 Maintenance

### Regular Tasks

1. **Monitor Bridge Health**
   - Set up health check monitoring
   - Alert if bridge becomes unavailable
   - Check disk space on Windows Server

2. **Review Logs**
   - Check for SQL connection errors
   - Monitor API request times
   - Review failed SOAP note posts

3. **Database Backups**
   - Backend sessions database (automated)
   - Dentrix SQL Server (handled by Dentrix)

### Updates

1. **Update Dentrix Bridge**
   ```powershell
   cd C:\DentrixBridge
   git pull  # If using git
   python -m pip install -r requirements.txt --upgrade
   Restart-Service DentrixBridge
   ```

2. **Update Backend**
   ```bash
   cd Backend
   git pull
   pip install -r requirements.txt --upgrade
   docker-compose restart backend
   ```

## 📚 Additional Resources

- [Dentrix Bridge API Documentation](../dentrix_bridge/README.md)
- [Dentrix DDP Documentation](https://www.dentrix.com/products/dentrix-enterprise/developer-program)
- [Microsoft ODBC Driver Documentation](https://docs.microsoft.com/en-us/sql/connect/odbc/)

## 🆘 Support

For Dentrix integration issues:
1. Check this guide's troubleshooting section
2. Review logs in both backend and bridge
3. Test each component independently
4. Verify network connectivity
5. Contact Dentrix support for DDP-specific issues

---

**Version:** 1.0  
**Last Updated:** January 2024  
**Maintained By:** Boise Prosthodontics AI Scribe Team
