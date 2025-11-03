"""
Dentrix Client - HTTP client for connecting to on-premise Dentrix Bridge
Provides methods to search patients, get details, and post SOAP notes to Dentrix
"""

import os
import logging
from typing import Dict, List, Optional
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class DentrixClient:
    """
    HTTP client for Dentrix Bridge Service
    
    Connects to on-premise Dentrix bridge to:
    - Search patients
    - Get patient demographics
    - Post SOAP notes
    - Get provider list
    """
    
    def __init__(self, bridge_url: Optional[str] = None):
        """
        Initialize Dentrix client
        
        Args:
            bridge_url: URL of Dentrix bridge service (defaults to env var)
        """
        self.bridge_url = bridge_url or os.getenv(
            'DENTRIX_BRIDGE_URL', 
            'http://localhost:8080'
        )
        self.timeout = 10  # seconds
        
        # Remove trailing slash
        self.bridge_url = self.bridge_url.rstrip('/')
        
        logger.info(f"Dentrix client initialized: {self.bridge_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make HTTP request to Dentrix bridge with error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            dict: Response JSON
            
        Raises:
            Exception: On connection or HTTP errors
        """
        url = f"{self.bridge_url}{endpoint}"
        
        try:
            logger.debug(f"{method} {url}")
            
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            response.raise_for_status()
            return response.json()
            
        except Timeout:
            error_msg = f"Dentrix bridge timeout: {url}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except ConnectionError:
            error_msg = f"Cannot connect to Dentrix bridge: {self.bridge_url}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except RequestException as e:
            error_msg = f"Dentrix bridge request failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def search_patients(self, query: str) -> List[Dict]:
        """
        Search for patients by name or chart number
        
        Args:
            query: Patient name or chart number to search
            
        Returns:
            list: List of patient search results
                [{patient_id, name, dob, chart_number, phone}, ...]
            
        Example:
            >>> client.search_patients("Smith")
            [{'patient_id': 12345, 'name': 'Smith, John', ...}]
        """
        try:
            logger.info(f"🔍 Searching Dentrix patients: '{query}'")
            
            response = self._make_request(
                'GET',
                '/api/patients/search',
                params={'query': query}
            )
            
            logger.info(f"✅ Found {len(response)} patients")
            return response
            
        except Exception as e:
            logger.error(f"Patient search failed: {e}")
            raise Exception(f"Failed to search Dentrix patients: {str(e)}")
    
    def get_patient(self, patient_id: str) -> Dict:
        """
        Get full patient details including demographics and insurance
        
        Args:
            patient_id: Dentrix patient ID
            
        Returns:
            dict: Complete patient information
                {patient_id, first_name, last_name, dob, insurance, ...}
            
        Example:
            >>> client.get_patient("12345")
            {'patient_id': 12345, 'first_name': 'John', ...}
        """
        try:
            logger.info(f"📋 Getting Dentrix patient details: ID {patient_id}")
            
            response = self._make_request(
                'GET',
                f'/api/patients/{patient_id}'
            )
            
            logger.info(f"✅ Retrieved patient: {response.get('first_name')} {response.get('last_name')}")
            return response
            
        except Exception as e:
            logger.error(f"Get patient failed: {e}")
            raise Exception(f"Failed to get Dentrix patient {patient_id}: {str(e)}")
    
    def create_soap_note(
        self, 
        patient_id: int, 
        provider_id: int, 
        soap_note: str,
        note_type: str = "SOAP",
        note_date: Optional[str] = None,
        appointment_id: Optional[int] = None
    ) -> Dict:
        """
        Post SOAP note to Dentrix
        
        Args:
            patient_id: Dentrix patient ID
            provider_id: Dentrix provider ID
            soap_note: Full SOAP note text
            note_type: Type of note (default: "SOAP")
            note_date: Date of note in YYYY-MM-DD format (default: today)
            appointment_id: Optional appointment ID to link
            
        Returns:
            dict: Response with note_id and success status
                {success: bool, note_id: int, message: str, timestamp: str}
            
        Example:
            >>> client.create_soap_note(
            ...     patient_id=12345,
            ...     provider_id=1,
            ...     soap_note="S: Patient presents with...\nO: ...\nA: ...\nP: ..."
            ... )
            {'success': True, 'note_id': 98765, ...}
        """
        try:
            logger.info(f"📝 Creating SOAP note in Dentrix: Patient {patient_id}, Provider {provider_id}")
            
            payload = {
                'patient_id': patient_id,
                'provider_id': provider_id,
                'note_type': note_type,
                'note_text': soap_note
            }
            
            if note_date:
                payload['note_date'] = note_date
            
            if appointment_id:
                payload['appointment_id'] = appointment_id
            
            response = self._make_request(
                'POST',
                '/api/clinical-notes',
                json=payload
            )
            
            if response.get('success'):
                logger.info(f"✅ SOAP note created in Dentrix: Note ID {response.get('note_id')}")
            else:
                logger.warning(f"⚠️ SOAP note creation returned success=False")
            
            return response
            
        except Exception as e:
            logger.error(f"Create SOAP note failed: {e}")
            raise Exception(f"Failed to create Dentrix SOAP note: {str(e)}")
    
    def get_providers(self) -> List[Dict]:
        """
        Get list of all providers from Dentrix
        
        Returns:
            list: List of providers
                [{provider_id, name, credentials, specialty, npi, license_number}, ...]
            
        Example:
            >>> client.get_providers()
            [{'provider_id': 1, 'name': 'Dr. Baguley', 'credentials': 'DDS', ...}]
        """
        try:
            logger.info("👨‍⚕️ Getting Dentrix providers list")
            
            response = self._make_request(
                'GET',
                '/api/providers'
            )
            
            logger.info(f"✅ Retrieved {len(response)} providers")
            return response
            
        except Exception as e:
            logger.error(f"Get providers failed: {e}")
            raise Exception(f"Failed to get Dentrix providers: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if Dentrix bridge is accessible and healthy
        
        Returns:
            bool: True if bridge is healthy, False otherwise
            
        Example:
            >>> client.health_check()
            True
        """
        try:
            logger.debug("🏥 Checking Dentrix bridge health")
            
            response = self._make_request(
                'GET',
                '/health'
            )
            
            is_healthy = (
                response.get('status') == 'healthy' and
                response.get('dentrix_connection') == True
            )
            
            if is_healthy:
                logger.info("✅ Dentrix bridge is healthy")
            else:
                logger.warning(f"⚠️ Dentrix bridge unhealthy: {response}")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Dentrix bridge health check failed: {e}")
            return False


# Singleton instance for easy access
_dentrix_client = None

def get_dentrix_client() -> DentrixClient:
    """
    Get singleton DentrixClient instance
    
    Returns:
        DentrixClient: Shared client instance
    """
    global _dentrix_client
    if _dentrix_client is None:
        _dentrix_client = DentrixClient()
    return _dentrix_client


if __name__ == "__main__":
    # Test Dentrix client
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("🧪 TESTING DENTRIX CLIENT")
    print("="*70)
    
    client = DentrixClient()
    
    print(f"\n📡 Bridge URL: {client.bridge_url}")
    print(f"⏱️ Timeout: {client.timeout}s")
    
    # Test health check
    print("\n🏥 Testing health check...")
    try:
        is_healthy = client.health_check()
        print(f"Health Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    print("\n" + "="*70 + "\n")
