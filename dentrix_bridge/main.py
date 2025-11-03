"""
Dentrix DDP API Bridge Service
On-premise FastAPI service that connects to Dentrix SQL Server database
Exposes REST API for patient lookup, demographics, and clinical note posting
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import pyodbc
from datetime import datetime, date
import os
import logging
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Dentrix DDP API Bridge",
    description="On-premise bridge service for Dentrix database integration",
    version="1.0.0"
)

# CORS configuration - allow cloud-based AI Scribe to connect
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class PatientSearch(BaseModel):
    """Patient search result"""
    patient_id: int
    name: str
    dob: Optional[str] = None
    chart_number: Optional[str] = None
    phone: Optional[str] = None

class Insurance(BaseModel):
    """Patient insurance information"""
    insurance_id: Optional[int] = None
    carrier_name: Optional[str] = None
    policy_number: Optional[str] = None
    group_number: Optional[str] = None
    subscriber_name: Optional[str] = None
    relationship: Optional[str] = None

class PatientDetail(BaseModel):
    """Full patient demographics"""
    patient_id: int
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    preferred_name: Optional[str] = None
    dob: Optional[str] = None
    ssn: Optional[str] = None
    chart_number: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    home_phone: Optional[str] = None
    work_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    primary_insurance: Optional[Insurance] = None
    secondary_insurance: Optional[Insurance] = None

class ClinicalNoteRequest(BaseModel):
    """Clinical note to insert into Dentrix"""
    patient_id: int = Field(..., description="Dentrix patient ID")
    provider_id: int = Field(..., description="Dentrix provider ID")
    note_type: str = Field(default="SOAP", description="Type of note (SOAP, Progress, etc.)")
    note_text: str = Field(..., description="Full note text including SOAP sections")
    note_date: Optional[str] = Field(default=None, description="Date of note (YYYY-MM-DD), defaults to today")
    appointment_id: Optional[int] = Field(default=None, description="Associated appointment ID if applicable")

class ClinicalNoteResponse(BaseModel):
    """Response after inserting clinical note"""
    success: bool
    note_id: Optional[int] = None
    message: str
    timestamp: str

class Provider(BaseModel):
    """Dentrix provider information"""
    provider_id: int
    name: str
    credentials: Optional[str] = None
    specialty: Optional[str] = None
    npi: Optional[str] = None
    license_number: Optional[str] = None

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    dentrix_connection: bool
    database_name: Optional[str] = None
    timestamp: str


class DentrixConnection:
    """
    Manages SQL Server connection to Dentrix database
    Uses Dentrix DDP (Data Distribution Protocol) stored procedures
    """
    
    def __init__(self):
        """Initialize connection parameters from environment variables"""
        self.server = os.getenv('DENTRIX_SQL_SERVER', 'localhost')
        self.database = os.getenv('DENTRIX_DATABASE', 'Dentrix')
        self.username = os.getenv('DENTRIX_SQL_USER', '')
        self.password = os.getenv('DENTRIX_SQL_PASSWORD', '')
        self.use_windows_auth = os.getenv('DENTRIX_USE_WINDOWS_AUTH', 'true').lower() == 'true'
        
        logger.info(f"Dentrix connection configured: Server={self.server}, Database={self.database}, WindowsAuth={self.use_windows_auth}")
    
    def get_connection(self) -> pyodbc.Connection:
        """
        Create and return database connection
        
        Returns:
            pyodbc.Connection: Active database connection
            
        Raises:
            Exception: If connection fails
        """
        try:
            if self.use_windows_auth:
                # Windows Authentication (recommended for on-premise)
                connection_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"Trusted_Connection=yes;"
                )
            else:
                # SQL Server Authentication
                connection_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    f"UID={self.username};"
                    f"PWD={self.password};"
                )
            
            conn = pyodbc.connect(connection_string, timeout=10)
            logger.debug("Database connection established successfully")
            return conn
            
        except pyodbc.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise Exception(f"Failed to connect to Dentrix database: {str(e)}")


# Initialize Dentrix connection handler
dentrix = DentrixConnection()


def parse_soap_note(note_text: str) -> Dict[str, str]:
    """
    Parse SOAP note text into structured sections
    
    Args:
        note_text: Full SOAP note text
        
    Returns:
        dict: Extracted SOAP sections {subjective, objective, assessment, plan}
    """
    sections = {
        'subjective': '',
        'objective': '',
        'assessment': '',
        'plan': ''
    }
    
    # Pattern to match SOAP section headers (case-insensitive)
    patterns = {
        'subjective': r'(?:^|\n)\s*(?:S:|Subjective:?)\s*(.+?)(?=\n\s*(?:O:|Objective:?|A:|Assessment:?|P:|Plan:?)|$)',
        'objective': r'(?:^|\n)\s*(?:O:|Objective:?)\s*(.+?)(?=\n\s*(?:A:|Assessment:?|P:|Plan:?)|$)',
        'assessment': r'(?:^|\n)\s*(?:A:|Assessment:?)\s*(.+?)(?=\n\s*(?:P:|Plan:?)|$)',
        'plan': r'(?:^|\n)\s*(?:P:|Plan:?)\s*(.+?)$'
    }
    
    for section, pattern in patterns.items():
        match = re.search(pattern, note_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections[section] = match.group(1).strip()
    
    return sections


# API Endpoints

@app.get("/api/patients/search", response_model=List[PatientSearch])
async def search_patients(
    query: str = Query(..., min_length=2, description="Patient name to search (minimum 2 characters)")
):
    """
    Search for patients by name
    
    Args:
        query: Patient name (last name, first name, or both)
        
    Returns:
        List of matching patients with basic info
    """
    try:
        conn = dentrix.get_connection()
        cursor = conn.cursor()
        
        # Call Dentrix DDP stored procedure
        # Note: Actual SP name may vary - adjust based on Dentrix version
        cursor.execute("EXEC sp_DDP_GetPatientsByName ?", query)
        
        results = []
        for row in cursor.fetchall():
            results.append(PatientSearch(
                patient_id=row.PatientID,
                name=f"{row.LastName}, {row.FirstName}",
                dob=row.BirthDate.strftime('%Y-%m-%d') if row.BirthDate else None,
                chart_number=row.ChartNumber,
                phone=row.HomePhone or row.MobilePhone
            ))
        
        cursor.close()
        conn.close()
        
        logger.info(f"Patient search '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Patient search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Patient search failed: {str(e)}")


@app.get("/api/patients/{patient_id}", response_model=PatientDetail)
async def get_patient(patient_id: int):
    """
    Get full patient details including demographics and insurance
    
    Args:
        patient_id: Dentrix patient ID
        
    Returns:
        Complete patient information
    """
    try:
        conn = dentrix.get_connection()
        cursor = conn.cursor()
        
        # Get patient demographics
        cursor.execute("EXEC sp_DDP_GetPatient ?", patient_id)
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
        
        # Get insurance information
        cursor.execute("EXEC sp_DDP_GetPatientInsurance ?", patient_id)
        insurance_rows = cursor.fetchall()
        
        primary_ins = None
        secondary_ins = None
        
        for ins_row in insurance_rows:
            insurance = Insurance(
                insurance_id=ins_row.InsuranceID,
                carrier_name=ins_row.CarrierName,
                policy_number=ins_row.PolicyNumber,
                group_number=ins_row.GroupNumber,
                subscriber_name=ins_row.SubscriberName,
                relationship=ins_row.Relationship
            )
            
            if ins_row.Priority == 1:
                primary_ins = insurance
            elif ins_row.Priority == 2:
                secondary_ins = insurance
        
        # Build patient detail object
        patient = PatientDetail(
            patient_id=row.PatientID,
            first_name=row.FirstName,
            last_name=row.LastName,
            middle_name=row.MiddleName,
            preferred_name=row.PreferredName,
            dob=row.BirthDate.strftime('%Y-%m-%d') if row.BirthDate else None,
            ssn=row.SSN,
            chart_number=row.ChartNumber,
            gender=row.Gender,
            marital_status=row.MaritalStatus,
            address=row.Address,
            city=row.City,
            state=row.State,
            zip_code=row.ZipCode,
            home_phone=row.HomePhone,
            work_phone=row.WorkPhone,
            mobile_phone=row.MobilePhone,
            email=row.Email,
            emergency_contact=row.EmergencyContact,
            emergency_phone=row.EmergencyPhone,
            primary_insurance=primary_ins,
            secondary_insurance=secondary_ins
        )
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved patient details for ID {patient_id}")
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get patient failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patient: {str(e)}")


@app.post("/api/clinical-notes", response_model=ClinicalNoteResponse)
async def create_clinical_note(note: ClinicalNoteRequest):
    """
    Insert clinical note into Dentrix
    
    Args:
        note: Clinical note details including patient, provider, and note text
        
    Returns:
        Success response with note ID
    """
    try:
        conn = dentrix.get_connection()
        cursor = conn.cursor()
        
        # Parse SOAP sections
        soap_sections = parse_soap_note(note.note_text)
        
        # Use provided date or default to today
        note_date = note.note_date if note.note_date else datetime.now().strftime('%Y-%m-%d')
        
        # Call Dentrix DDP stored procedure to insert clinical note
        # Note: Parameters may vary based on Dentrix version
        cursor.execute(
            "EXEC sp_DDP_InsertClinicalNote ?, ?, ?, ?, ?, ?, ?, ?, ?",
            note.patient_id,
            note.provider_id,
            note.note_type,
            note_date,
            note.note_text,
            soap_sections['subjective'],
            soap_sections['objective'],
            soap_sections['assessment'],
            soap_sections['plan']
        )
        
        # Get the new note ID
        note_id = cursor.fetchval()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Clinical note created: ID={note_id}, Patient={note.patient_id}, Provider={note.provider_id}")
        
        return ClinicalNoteResponse(
            success=True,
            note_id=note_id,
            message=f"Clinical note successfully created for patient {note.patient_id}",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Create clinical note failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create clinical note: {str(e)}")


@app.get("/api/providers", response_model=List[Provider])
async def get_providers():
    """
    Get list of all providers in Dentrix
    
    Returns:
        List of providers with credentials and specialty
    """
    try:
        conn = dentrix.get_connection()
        cursor = conn.cursor()
        
        # Call Dentrix DDP stored procedure
        cursor.execute("EXEC sp_DDP_GetProviders")
        
        providers = []
        for row in cursor.fetchall():
            providers.append(Provider(
                provider_id=row.ProviderID,
                name=f"{row.FirstName} {row.LastName}",
                credentials=row.Credentials,
                specialty=row.Specialty,
                npi=row.NPI,
                license_number=row.LicenseNumber
            ))
        
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(providers)} providers")
        return providers
        
    except Exception as e:
        logger.error(f"Get providers failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve providers: {str(e)}")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint - tests database connection
    
    Returns:
        Health status including database connectivity
    """
    dentrix_ok = False
    db_name = None
    
    try:
        conn = dentrix.get_connection()
        cursor = conn.cursor()
        
        # Simple query to test connection
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        dentrix_ok = True
        logger.info("Health check passed")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return HealthCheck(
        status="healthy" if dentrix_ok else "unhealthy",
        dentrix_connection=dentrix_ok,
        database_name=db_name,
        timestamp=datetime.now().isoformat()
    )


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "Dentrix DDP API Bridge",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "patient_search": "/api/patients/search?query=<name>",
            "patient_detail": "/api/patients/{patient_id}",
            "providers": "/api/providers",
            "create_note": "/api/clinical-notes"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run on port 8080
    port = int(os.getenv('DENTRIX_BRIDGE_PORT', '8080'))
    host = os.getenv('DENTRIX_BRIDGE_HOST', '0.0.0.0')
    
    logger.info(f"Starting Dentrix DDP API Bridge on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
