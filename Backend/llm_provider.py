"""
LLM Provider Abstraction Layer
Supports both Ollama (free, local) and OpenAI (paid, cloud) for SOAP note generation
"""

import os
import logging
import requests
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"


class LLMConfig:
    """Configuration for LLM provider"""
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OLLAMA,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama3.1:8b",
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini"
    ):
        self.provider = provider
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
    
    @classmethod
    def load_from_env(cls) -> 'LLMConfig':
        """Load configuration from environment variables"""
        
        # Get provider from environment (default: ollama)
        provider_str = os.getenv('LLM_PROVIDER', 'ollama').lower()
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            logger.warning(f"Invalid LLM_PROVIDER '{provider_str}', defaulting to ollama")
            provider = LLMProvider.OLLAMA
        
        # Ollama configuration
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
        
        # OpenAI configuration
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Validate OpenAI configuration if selected
        if provider == LLMProvider.OPENAI and not openai_api_key:
            logger.error("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set!")
            logger.warning("Falling back to Ollama provider")
            provider = LLMProvider.OLLAMA
        
        config = cls(
            provider=provider,
            ollama_host=ollama_host,
            ollama_model=ollama_model,
            openai_api_key=openai_api_key,
            openai_model=openai_model
        )
        
        logger.info(f"LLM Provider: {config.provider.value}")
        if config.provider == LLMProvider.OLLAMA:
            logger.info(f"Ollama Host: {config.ollama_host}")
            logger.info(f"Ollama Model: {config.ollama_model}")
        else:
            logger.info(f"OpenAI Model: {config.openai_model}")
        
        return config
    
    def get_info(self) -> Dict:
        """Get provider info (without sensitive data like API keys)"""
        info = {
            "provider": self.provider.value,
            "model": None,
            "host": None
        }
        
        if self.provider == LLMProvider.OLLAMA:
            info["model"] = self.ollama_model
            info["host"] = self.ollama_host
        else:
            info["model"] = self.openai_model
            info["host"] = "api.openai.com"
        
        return info


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def generate_soap_note(self, transcript: str, template: Dict) -> str:
        """Generate SOAP note from transcript using template"""
        pass
    
    @abstractmethod
    def edit_soap_note(self, soap_note: str, instruction: str) -> str:
        """Edit existing SOAP note based on user instruction"""
        pass
    
    @abstractmethod
    def answer_question(self, soap_note: str, question: str) -> str:
        """Answer question about SOAP note"""
        pass


class OllamaClient(BaseLLMClient):
    """Ollama LLM client implementation"""
    
    def __init__(self, host: str, model: str):
        self.host = host.rstrip('/')
        self.model = model
        logger.info(f"Initialized OllamaClient: {host} with model {model}")
    
    def _generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate response from Ollama"""
        try:
            url = f"{self.host}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            if system:
                payload["system"] = system
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '').strip()
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise Exception("LLM request timed out after 120 seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    def generate_soap_note(self, transcript: str, template: Dict) -> str:
        """Generate SOAP note from transcript"""
        
        template_name = template.get('name', 'Default')
        sections = template.get('sections', {})
        
        # Build system prompt
        system = f"""You are a medical scribe assistant specializing in prosthodontics. 
Your task is to convert clinical conversations into professional SOAP notes using the {template_name} template.
Be precise, concise, and maintain medical terminology standards."""
        
        # Build user prompt with template structure
        prompt = f"""Convert the following clinical transcript into a structured SOAP note.

Template: {template_name}

Expected Sections:
"""
        for section_key, section_info in sections.items():
            section_title = section_info.get('title', section_key.upper())
            section_desc = section_info.get('description', '')
            prompt += f"\n{section_title}:\n{section_desc}\n"
        
        prompt += f"\n\nTranscript:\n{transcript}\n\nGenerate a complete SOAP note:"
        
        logger.info(f"Generating SOAP note with Ollama ({self.model})")
        return self._generate(prompt, system)
    
    def edit_soap_note(self, soap_note: str, instruction: str) -> str:
        """Edit SOAP note based on instruction"""
        
        system = """You are a medical documentation assistant. 
Edit SOAP notes according to user instructions while maintaining medical accuracy and professional format.
Return ONLY the updated SOAP note, no explanations."""
        
        prompt = f"""Current SOAP Note:
{soap_note}

User Request:
{instruction}

Provide the updated SOAP note:"""
        
        logger.info(f"Editing SOAP note with Ollama ({self.model})")
        return self._generate(prompt, system)
    
    def answer_question(self, soap_note: str, question: str) -> str:
        """Answer question about SOAP note"""
        
        system = """You are a helpful medical documentation assistant.
Answer questions about SOAP notes clearly and concisely.
Provide professional, accurate responses."""
        
        prompt = f"""SOAP Note:
{soap_note}

Question:
{question}

Answer:"""
        
        logger.info(f"Answering question with Ollama ({self.model})")
        return self._generate(prompt, system)


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
            logger.info(f"Initialized OpenAIClient with model {model}")
        except ImportError:
            logger.error("OpenAI library not installed. Run: pip install openai>=1.0.0")
            raise ImportError("OpenAI library required for OpenAI provider")
    
    def _chat_completion(self, messages: list) -> str:
        """Get chat completion from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent medical documentation
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI request failed: {str(e)}")
    
    def generate_soap_note(self, transcript: str, template: Dict) -> str:
        """Generate SOAP note from transcript"""
        
        template_name = template.get('name', 'Default')
        sections = template.get('sections', {})
        
        # Build template structure description
        sections_desc = ""
        for section_key, section_info in sections.items():
            section_title = section_info.get('title', section_key.upper())
            section_desc = section_info.get('description', '')
            sections_desc += f"\n{section_title}:\n{section_desc}\n"
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a medical scribe assistant specializing in prosthodontics.
Convert clinical conversations into professional SOAP notes using the {template_name} template.
Be precise, concise, and maintain medical terminology standards."""
            },
            {
                "role": "user",
                "content": f"""Convert the following clinical transcript into a structured SOAP note.

Template: {template_name}

Expected Sections:
{sections_desc}

Transcript:
{transcript}

Generate a complete SOAP note:"""
            }
        ]
        
        logger.info(f"Generating SOAP note with OpenAI ({self.model})")
        return self._chat_completion(messages)
    
    def edit_soap_note(self, soap_note: str, instruction: str) -> str:
        """Edit SOAP note based on instruction"""
        
        messages = [
            {
                "role": "system",
                "content": """You are a medical documentation assistant.
Edit SOAP notes according to user instructions while maintaining medical accuracy and professional format.
Return ONLY the updated SOAP note, no explanations."""
            },
            {
                "role": "user",
                "content": f"""Current SOAP Note:
{soap_note}

User Request:
{instruction}

Provide the updated SOAP note:"""
            }
        ]
        
        logger.info(f"Editing SOAP note with OpenAI ({self.model})")
        return self._chat_completion(messages)
    
    def answer_question(self, soap_note: str, question: str) -> str:
        """Answer question about SOAP note"""
        
        messages = [
            {
                "role": "system",
                "content": """You are a helpful medical documentation assistant.
Answer questions about SOAP notes clearly and concisely.
Provide professional, accurate responses."""
            },
            {
                "role": "user",
                "content": f"""SOAP Note:
{soap_note}

Question:
{question}

Answer:"""
            }
        ]
        
        logger.info(f"Answering question with OpenAI ({self.model})")
        return self._chat_completion(messages)


def get_llm_client(config: LLMConfig) -> BaseLLMClient:
    """
    Factory function to get appropriate LLM client based on configuration
    
    Args:
        config: LLMConfig instance
        
    Returns:
        BaseLLMClient: Ollama or OpenAI client instance
    """
    if config.provider == LLMProvider.OLLAMA:
        return OllamaClient(
            host=config.ollama_host,
            model=config.ollama_model
        )
    elif config.provider == LLMProvider.OPENAI:
        return OpenAIClient(
            api_key=config.openai_api_key,
            model=config.openai_model
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.provider}")


# Convenience function for getting client from environment
def get_llm_client_from_env() -> BaseLLMClient:
    """Get LLM client from environment variables"""
    config = LLMConfig.load_from_env()
    return get_llm_client(config)


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*70)
    print("LLM PROVIDER ABSTRACTION TEST")
    print("="*70)
    
    # Test configuration loading
    print("\n📋 Loading configuration from environment...")
    config = LLMConfig.load_from_env()
    print(f"Provider: {config.provider.value}")
    print(f"Info: {json.dumps(config.get_info(), indent=2)}")
    
    # Test client creation
    print("\n🔧 Creating LLM client...")
    try:
        client = get_llm_client(config)
        print(f"✅ Client created: {client.__class__.__name__}")
        
        # Simple test (won't actually call API without proper setup)
        print("\n✅ LLM abstraction layer is ready!")
        print(f"Using: {config.provider.value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*70 + "\n")
