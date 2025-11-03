# 🚀 Dentrix Integration - Quick Start Guide

**Last Updated:** November 3, 2025  
**Status:** ✅ Backend Complete | ⏸️ Bridge Ready for Deployment

---

## ⚡ Quick Reference

### Test Integration
```bash
# Run inside Docker container
docker exec boise_new_backend python test_dentrix_integration.py

# Expected: 4/4 tests pass (1 skipped if bridge not deployed)
```

### Check Backend Health
```powershell
# Test Dentrix health endpoint
Invoke-WebRequest -Uri http://localhost:3051/api/dentrix/health
```

### Run Database Migration
```bash
# If database already exists, run migration
docker exec boise_new_backend python migrate_add_dentrix_columns.py
```

---

## 📂 File Locations

### On-Premise Bridge Files
```
dentrix_bridge/
├── main.py              # FastAPI service (550+ lines)
├── Dockerfile           # Container config with ODBC Driver 18
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
└── README.md            # Complete documentation (400+ lines)
```

### Cloud Backend Files
```
Backend/
├── dentrix_client.py                    # HTTP client (280+ lines)
├── main.py                              # Added 5 Dentrix endpoints
├── database.py                          # Added 4 Dentrix columns
├── migrate_add_dentrix_columns.py       # Migration script
└── test_dentrix_integration.py          # Integration tests
```

---

## 🔌 API Endpoints

### Backend (localhost:3051)
```http
GET  /api/dentrix/health
GET  /api/dentrix/patients/search?query=Smith
GET  /api/dentrix/patients/12345
POST /api/sessions/{session_id}/send-to-dentrix
GET  /api/dentrix/providers
```

### Bridge (localhost:8080) - When Deployed
```http
GET  /health
GET  /api/patients/search?query=Smith
GET  /api/patients/12345
POST /api/clinical-notes
GET  /api/providers
```

---

## 🏗️ Deployment Steps

### 1. Backend (Cloud) ✅ COMPLETE
```bash
# Already done:
✅ Created dentrix_client.py
✅ Added 5 endpoints to main.py
✅ Updated database.py schema
✅ Ran migration script
✅ Restarted backend
✅ All tests passing
```

### 2. Bridge (On-Premise) ⏸️ TODO
```powershell
# On Windows Server at dental office:

# 1. Copy files
Copy-Item -Recurse dentrix_bridge C:\DentrixBridge

# 2. Install dependencies
cd C:\DentrixBridge
python -m pip install -r requirements.txt

# 3. Configure
Copy-Item .env.example .env
notepad .env  # Edit with Dentrix SQL Server settings

# 4. Test
python main.py
# Visit: http://localhost:8080/health

# 5. Install as service (optional)
nssm install DentrixBridge python.exe C:\DentrixBridge\main.py
nssm start DentrixBridge
```

### 3. Connect Backend to Bridge
```bash
# Add to Backend/.env or environment:
DENTRIX_BRIDGE_URL=http://your-office-ip:8080

# Or if using domain/reverse proxy:
DENTRIX_BRIDGE_URL=https://dentrix.youroffice.com

# Restart backend:
docker-compose restart backend
```

---

## 🧪 Testing Workflow

### Test Backend Endpoints
```powershell
# Health check
Invoke-WebRequest http://localhost:3051/api/dentrix/health

# Expected: {"success":true,"dentrix_available":false,...}
# (false is normal if bridge not deployed)
```

### Test Bridge (After Deployment)
```powershell
# On Windows Server
Invoke-WebRequest http://localhost:8080/health

# Expected: {"status":"healthy","dentrix_connection":true}
```

### Test End-to-End
```bash
# From backend container
docker exec boise_new_backend python -c "
from dentrix_client import get_dentrix_client
client = get_dentrix_client()
healthy = client.health_check()
print(f'Bridge healthy: {healthy}')
"
```

---

## 🔍 Troubleshooting

### Backend Can't Connect to Bridge
```powershell
# 1. Check bridge is running
Invoke-WebRequest http://your-office:8080/health

# 2. Check firewall allows port 8080
Test-NetConnection -ComputerName your-office -Port 8080

# 3. Verify DENTRIX_BRIDGE_URL environment variable
docker exec boise_new_backend printenv DENTRIX_BRIDGE_URL
```

### Bridge Can't Connect to SQL Server
```powershell
# 1. Test SQL Server connection
sqlcmd -S localhost -d Dentrix -E

# 2. Check ODBC driver installed
odbcinst -q -d

# 3. Verify Dentrix database name
sqlcmd -S localhost -Q "SELECT name FROM sys.databases"
```

### Database Migration Issues
```bash
# 1. Check database exists
docker exec boise_new_backend ls -la /app/data/sessions.db

# 2. Run migration manually
docker exec boise_new_backend python migrate_add_dentrix_columns.py

# 3. Verify columns added
docker exec boise_new_backend python -c "
import sqlite3
conn = sqlite3.connect('/app/data/sessions.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(sessions)')
columns = [row[1] for row in cursor.fetchall()]
print([c for c in columns if 'dentrix' in c])
"
```

---

## 📊 Database Schema

### New Session Columns
```sql
sent_to_dentrix     BOOLEAN   DEFAULT 0       -- Was this sent to Dentrix?
dentrix_sent_at     DATETIME                  -- When was it sent?
dentrix_note_id     VARCHAR                   -- Dentrix clinical note ID
dentrix_patient_id  VARCHAR                   -- Dentrix patient ID
```

### Update Function
```python
from database import update_session_dentrix_status

update_session_dentrix_status(
    session_id="session123",
    dentrix_note_id="98765",
    dentrix_patient_id="12345",
    sent_to_dentrix=True
)
```

---

## 🔐 Security Checklist

### Network Security
- [ ] Use VPN or secure tunnel for cloud-to-premise
- [ ] Enable HTTPS/TLS on all connections
- [ ] Restrict port 8080 to known IPs
- [ ] Use reverse proxy for bridge (optional)

### Database Security
- [ ] Use Windows Authentication for SQL Server
- [ ] Encrypt SQL Server connections (ODBC Driver 18)
- [ ] No SQL credentials in .env (use Windows Auth)

### HIPAA Compliance
- [ ] Verify PHI stays on-premise
- [ ] No PHI in cloud database
- [ ] No PHI in log files
- [ ] Audit trail enabled (session tracking)

---

## 📞 Support

### Documentation
- **Complete Guide:** `DENTRIX_INTEGRATION_GUIDE.md` (500+ lines)
- **Bridge Docs:** `dentrix_bridge/README.md` (400+ lines)
- **Implementation:** `DENTRIX_IMPLEMENTATION_SUMMARY.md`

### Test Commands
```bash
# Run all integration tests
docker exec boise_new_backend python test_dentrix_integration.py

# Test specific component
docker exec boise_new_backend python dentrix_client.py

# Check backend logs
docker logs --tail 50 boise_new_backend
```

---

## ✅ Success Indicators

### Backend is Ready
```bash
✅ test_dentrix_integration.py shows 4/4 passing
✅ GET /api/dentrix/health returns 200
✅ docker logs shows "Application startup complete"
✅ Database has 4 Dentrix columns
```

### Bridge is Working (After Deployment)
```powershell
✅ http://localhost:8080/health returns "healthy"
✅ Can query patients from Dentrix
✅ Can post SOAP notes to Dentrix
✅ Backend health check shows dentrix_available: true
```

---

**Quick Start:** Run integration tests, deploy bridge, connect and test! 🚀
