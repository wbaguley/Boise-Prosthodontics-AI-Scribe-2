"""
Medical Vocabulary Manager for Whisper Prompting
Provides specialty-specific medical terminology to improve transcription accuracy
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MedicalVocabulary:
    """
    Medical vocabulary manager for Whisper initial prompt optimization
    
    Whisper performs better when given context-specific terminology in the
    initial_prompt parameter. This class provides curated medical vocabulary
    for different dental specialties to improve transcription accuracy.
    """
    
    # Common dental terminology used across all specialties
    GENERAL_DENTAL_TERMS = [
        "tooth", "teeth", "incisor", "canine", "premolar", "molar",
        "enamel", "dentin", "pulp", "root canal", "gingiva", "gums",
        "periodontal", "occlusion", "malocclusion", "bite",
        "maxillary", "mandibular", "anterior", "posterior",
        "buccal", "lingual", "mesial", "distal", "palatal",
        "caries", "decay", "cavity", "filling", "restoration",
        "extraction", "anesthesia", "novocaine", "lidocaine",
        "radiograph", "x-ray", "panoramic", "periapical",
        "prophylaxis", "cleaning", "scaling", "polishing",
        "plaque", "tartar", "calculus", "gingivitis",
        "fluoride", "sealant", "composite", "amalgam",
        "local anesthesia", "topical anesthetic"
    ]
    
    # Prosthodontics-specific terminology
    PROSTHODONTICS_TERMS = [
        "crown", "bridge", "implant", "denture", "abutment",
        "pontic", "retainer", "fixed partial denture", "FPD",
        "removable partial denture", "RPD", "complete denture",
        "overdenture", "implant-supported", "All-on-4", "All-on-6",
        "zirconia", "porcelain", "ceramic", "PFM", "porcelain-fused-to-metal",
        "provisional", "temporary crown", "permanent crown",
        "prep", "preparation", "margin", "subgingival", "supragingival",
        "impression", "alginate", "polyvinyl siloxane", "PVS",
        "bite registration", "centric occlusion", "centric relation",
        "articulator", "facebow", "shade selection", "shade matching",
        "cementation", "luting", "try-in", "veneer", "onlay", "inlay",
        "Maryland bridge", "cantilever bridge", "resin-bonded",
        "osseointegration", "screw-retained", "cement-retained",
        "healing abutment", "cover screw", "implant analog",
        "coping", "framework", "metal framework", "CAD-CAM",
        "digital impression", "intraoral scanner", "IOS",
        "shade tab", "VITA shade", "monolithic", "layered"
    ]
    
    # Periodontics terminology
    PERIODONTICS_TERMS = [
        "periodontitis", "gingivitis", "periodontal disease",
        "pocket depth", "probing depth", "clinical attachment level", "CAL",
        "bone loss", "horizontal bone loss", "vertical bone loss",
        "furcation", "recession", "gingival recession",
        "scaling and root planing", "SRP", "debridement",
        "curettage", "flap surgery", "osseous surgery",
        "bone graft", "guided tissue regeneration", "GTR",
        "membrane", "barrier membrane", "ePTFE",
        "connective tissue graft", "CTG", "free gingival graft", "FGG",
        "laser therapy", "antimicrobial", "chlorhexidine",
        "pocket reduction", "crown lengthening",
        "mucogingival", "attached gingiva", "keratinized tissue"
    ]
    
    # Endodontics terminology
    ENDODONTICS_TERMS = [
        "root canal", "RCT", "endodontic therapy",
        "pulp", "pulpitis", "irreversible pulpitis", "reversible pulpitis",
        "necrotic pulp", "pulp chamber", "root canal system",
        "apex", "apical", "periapical", "periapical lesion",
        "abscess", "apical abscess", "fistula", "sinus tract",
        "file", "rotary file", "hand file", "reamer",
        "irrigation", "sodium hypochlorite", "NaOCl", "EDTA",
        "obturation", "gutta-percha", "sealer",
        "access cavity", "working length", "apical constriction",
        "retreatment", "apicoectomy", "apical surgery",
        "calcium hydroxide", "MTA", "mineral trioxide aggregate",
        "pulpotomy", "pulpectomy", "vital pulp therapy"
    ]
    
    # Orthodontics terminology
    ORTHODONTICS_TERMS = [
        "braces", "brackets", "wires", "archwire",
        "elastics", "rubber bands", "ligature", "power chain",
        "malocclusion", "Class I", "Class II", "Class III",
        "overbite", "overjet", "crossbite", "open bite",
        "spacing", "crowding", "diastema", "midline",
        "expansion", "palatal expander", "rapid palatal expansion", "RPE",
        "Invisalign", "clear aligners", "aligner therapy",
        "retainer", "Hawley retainer", "fixed retainer",
        "headgear", "elastics", "interproximal reduction", "IPR",
        "bonding", "debonding", "cephalometric", "lateral ceph",
        "extraction", "non-extraction", "anchorage"
    ]
    
    # Oral surgery terminology
    ORAL_SURGERY_TERMS = [
        "extraction", "surgical extraction", "simple extraction",
        "impacted tooth", "wisdom teeth", "third molars",
        "socket preservation", "ridge augmentation",
        "bone graft", "sinus lift", "sinus augmentation",
        "incision", "flap", "suture", "suturing",
        "anesthesia", "general anesthesia", "IV sedation",
        "conscious sedation", "nitrous oxide",
        "osteotomy", "alveoloplasty", "ridge reduction",
        "biopsy", "pathology", "lesion", "cyst",
        "TMJ", "temporomandibular joint", "TMD",
        "dry socket", "alveolar osteitis", "postoperative"
    ]
    
    # Common medications and materials
    MEDICATIONS_MATERIALS = [
        "ibuprofen", "acetaminophen", "Tylenol", "Advil",
        "amoxicillin", "penicillin", "clindamycin", "azithromycin",
        "hydrocodone", "Vicodin", "oxycodone", "Percocet",
        "chlorhexidine", "Peridex", "fluoride", "sodium fluoride",
        "articaine", "septocaine", "mepivacaine", "carbocaine",
        "epinephrine", "vasoconstrictor",
        "composite resin", "flowable composite", "bulk fill",
        "glass ionomer", "resin-modified glass ionomer", "RMGI",
        "zinc oxide eugenol", "IRM", "Cavit"
    ]
    
    # Anatomical terms
    ANATOMICAL_TERMS = [
        "maxilla", "maxillary", "mandible", "mandibular",
        "anterior", "posterior", "lateral", "medial",
        "buccal", "lingual", "palatal", "labial",
        "mesial", "distal", "occlusal", "incisal",
        "facial", "vestibular", "interproximal",
        "alveolar bone", "cortical bone", "cancellous bone",
        "sinus", "maxillary sinus", "antrum",
        "TMJ", "condyle", "fossa", "eminence",
        "muscle", "masseter", "temporalis", "pterygoid"
    ]
    
    def __init__(self):
        """Initialize the medical vocabulary manager"""
        self.specialty_terms = {
            "general": self.GENERAL_DENTAL_TERMS,
            "dental": self.GENERAL_DENTAL_TERMS,
            "prosthodontics": self.PROSTHODONTICS_TERMS,
            "periodontics": self.PERIODONTICS_TERMS,
            "endodontics": self.ENDODONTICS_TERMS,
            "orthodontics": self.ORTHODONTICS_TERMS,
            "oral_surgery": self.ORAL_SURGERY_TERMS,
            "surgery": self.ORAL_SURGERY_TERMS,
        }
        
        logger.info("Medical vocabulary manager initialized")
    
    def get_dental_prompt(self) -> str:
        """
        Get general dental terminology prompt for Whisper
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of common dental terms
        """
        # Essential general dental terms only
        essential_terms = [
            "tooth", "teeth", "molar", "premolar", "incisor", "canine",
            "cavity", "filling", "crown", "extraction", "root canal",
            "gums", "periodontal", "bite", "occlusion",
            "maxillary", "mandibular", "anterior", "posterior",
            "buccal", "lingual", "mesial", "distal",
            "x-ray", "anesthesia", "cleaning", "plaque",
            "fluoride", "composite", "amalgam"
        ]
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized dental prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_prosthodontics_prompt(self) -> str:
        """
        Get prosthodontics-specific terminology prompt for Whisper
        
        Includes: crown, bridge, implant, denture, abutment, occlusion,
        maxillary, mandibular, and other prosthodontics terms
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of prosthodontics terms
        """
        # Use only the most critical prosthodontics terms to stay under token limit
        essential_terms = [
            # Core prosthodontics procedures
            "crown", "bridge", "implant", "denture", "abutment",
            "pontic", "FPD", "RPD", "All-on-4",
            # Materials
            "zirconia", "porcelain", "PFM", "ceramic",
            "provisional", "temporary crown", "permanent crown",
            # Procedures
            "prep", "impression", "occlusion", "cementation",
            "try-in", "veneer", "onlay", "inlay",
            "osseointegration", "screw-retained", "cement-retained",
            # Anatomy
            "maxillary", "mandibular", "anterior", "posterior",
            "buccal", "lingual", "mesial", "distal",
            # General dental essentials
            "tooth", "teeth", "molar", "premolar", "incisor",
            "bite", "margin", "shade", "centric"
        ]
        
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized prosthodontics prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_periodontics_prompt(self) -> str:
        """
        Get periodontics-specific terminology prompt
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of periodontics terms
        """
        essential_terms = [
            # Core periodontics
            "periodontitis", "gingivitis", "pocket depth", "probing",
            "bone loss", "recession", "furcation",
            "scaling", "root planing", "SRP", "debridement",
            "flap surgery", "bone graft", "GTR",
            "membrane", "gingival graft", "connective tissue",
            # Anatomy
            "gingiva", "gums", "periodontal", "attached gingiva",
            "maxillary", "mandibular", "buccal", "lingual",
            # General
            "tooth", "teeth", "molar", "bite", "occlusion"
        ]
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized periodontics prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_endodontics_prompt(self) -> str:
        """
        Get endodontics-specific terminology prompt
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of endodontics terms
        """
        essential_terms = [
            # Core endodontics
            "root canal", "RCT", "endodontic",
            "pulp", "pulpitis", "necrotic", "abscess",
            "apex", "apical", "periapical",
            "file", "irrigation", "obturation", "gutta-percha",
            "access cavity", "working length",
            "retreatment", "apicoectomy",
            "calcium hydroxide", "MTA",
            # Anatomy
            "maxillary", "mandibular", "molar", "premolar",
            "buccal", "lingual", "mesial", "distal",
            # General
            "tooth", "teeth", "crown", "anesthesia"
        ]
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized endodontics prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_orthodontics_prompt(self) -> str:
        """
        Get orthodontics-specific terminology prompt
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of orthodontics terms
        """
        essential_terms = [
            # Core orthodontics
            "braces", "brackets", "wires", "archwire",
            "elastics", "malocclusion", "Class I", "Class II", "Class III",
            "overbite", "overjet", "crossbite", "open bite",
            "spacing", "crowding", "expansion",
            "Invisalign", "aligners", "retainer",
            "IPR", "bonding", "cephalometric",
            # Anatomy
            "maxillary", "mandibular", "anterior", "posterior",
            "buccal", "lingual", "mesial", "distal",
            # General
            "tooth", "teeth", "molar", "premolar", "bite", "occlusion"
        ]
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized orthodontics prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_oral_surgery_prompt(self) -> str:
        """
        Get oral surgery-specific terminology prompt
        
        OPTIMIZED: Only essential terms to stay under 224 token limit
        
        Returns:
            str: Comma-separated list of oral surgery terms
        """
        essential_terms = [
            # Core oral surgery
            "extraction", "surgical extraction", "impacted",
            "wisdom teeth", "third molars",
            "socket preservation", "bone graft",
            "sinus lift", "sinus augmentation",
            "incision", "flap", "suture",
            "anesthesia", "sedation", "IV sedation", "nitrous oxide",
            "osteotomy", "biopsy", "lesion", "cyst",
            "TMJ", "dry socket",
            # Anatomy
            "maxillary", "mandibular", "anterior", "posterior",
            "buccal", "lingual", "alveolar", "sinus",
            # General
            "tooth", "teeth", "molar", "bone"
        ]
        prompt = ", ".join(essential_terms)
        logger.debug(f"Generated optimized oral surgery prompt with {len(essential_terms)} terms")
        return prompt
    
    def get_prompt_for_specialty(self, specialty: str) -> str:
        """
        Get specialty-specific vocabulary prompt for Whisper
        
        Args:
            specialty: Dental specialty name. Supported values:
                - "general" or "dental": General dentistry
                - "prosthodontics": Prosthodontics
                - "periodontics": Periodontics
                - "endodontics": Endodontics
                - "orthodontics": Orthodontics
                - "oral_surgery" or "surgery": Oral surgery
        
        Returns:
            str: Comma-separated list of specialty-specific terms
            
        Examples:
            >>> vocab = MedicalVocabulary()
            >>> prompt = vocab.get_prompt_for_specialty("prosthodontics")
            >>> # Returns: "tooth, crown, bridge, implant, denture..."
        """
        specialty_lower = specialty.lower().strip()
        
        # Map specialty to appropriate prompt method
        prompt_methods = {
            "general": self.get_dental_prompt,
            "dental": self.get_dental_prompt,
            "prosthodontics": self.get_prosthodontics_prompt,
            "periodontics": self.get_periodontics_prompt,
            "endodontics": self.get_endodontics_prompt,
            "orthodontics": self.get_orthodontics_prompt,
            "oral_surgery": self.get_oral_surgery_prompt,
            "surgery": self.get_oral_surgery_prompt,
        }
        
        if specialty_lower in prompt_methods:
            logger.info(f"Generating vocabulary prompt for specialty: {specialty}")
            return prompt_methods[specialty_lower]()
        else:
            logger.warning(f"Unknown specialty '{specialty}', using general dental prompt")
            return self.get_dental_prompt()
    
    def get_custom_prompt(self, additional_terms: List[str]) -> str:
        """
        Get custom prompt with additional provider-specific terms
        
        OPTIMIZED: Combines essential general terms with custom terms
        
        Args:
            additional_terms: List of custom terms to include
            
        Returns:
            str: Comma-separated list including essential dental and custom terms
        """
        # Use minimal base terms to leave room for custom terms
        base_terms = [
            "tooth", "teeth", "crown", "implant", "bridge",
            "maxillary", "mandibular", "occlusion", "bite",
            "anesthesia", "extraction", "filling"
        ]
        all_terms = base_terms + additional_terms
        prompt = ", ".join(all_terms)
        
        logger.info(f"Generated custom prompt with {len(all_terms)} terms ({len(additional_terms)} custom)")
        return prompt
    
    def get_all_specialties(self) -> List[str]:
        """
        Get list of all supported specialties
        
        Returns:
            list: Supported specialty names
        """
        return [
            "general",
            "prosthodontics",
            "periodontics",
            "endodontics",
            "orthodontics",
            "oral_surgery"
        ]
    
    def get_specialty_info(self, specialty: str) -> Dict:
        """
        Get detailed information about a specialty's vocabulary
        
        Args:
            specialty: Specialty name
            
        Returns:
            dict: Information about the specialty vocabulary
        """
        prompt = self.get_prompt_for_specialty(specialty)
        term_count = len(prompt.split(", "))
        
        specialty_lower = specialty.lower().strip()
        specialty_terms = self.specialty_terms.get(specialty_lower, [])
        
        return {
            "specialty": specialty,
            "total_terms": term_count,
            "specialty_specific_terms": len(specialty_terms),
            "includes_general_dental": True,
            "includes_anatomical": True,
            "prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt
        }
    
    def print_specialty_summary(self):
        """Print a formatted summary of all specialties"""
        print("\n" + "="*60)
        print("🦷 MEDICAL VOCABULARY MANAGER")
        print("="*60)
        print("\nSupported Dental Specialties:\n")
        
        for specialty in self.get_all_specialties():
            info = self.get_specialty_info(specialty)
            print(f"📌 {specialty.upper()}")
            print(f"   Total Terms: {info['total_terms']}")
            print(f"   Specialty Terms: {info['specialty_specific_terms']}")
            print(f"   Preview: {info['prompt_preview'][:80]}...")
            print()
        
        print("="*60)
        print("\n💡 Usage:")
        print("   vocab = MedicalVocabulary()")
        print("   prompt = vocab.get_prompt_for_specialty('prosthodontics')")
        print("   # Use prompt with Whisper's initial_prompt parameter")
        print("="*60 + "\n")
    
    def validate_prompt_length(self, prompt: str, max_tokens: int = 224) -> Dict:
        """
        Validate that prompt doesn't exceed Whisper's token limit
        
        Whisper has a maximum initial_prompt length of 224 tokens.
        This method estimates token count (rough approximation).
        
        Args:
            prompt: The prompt string to validate
            max_tokens: Maximum allowed tokens (default: 224)
            
        Returns:
            dict: Validation result with warnings if needed
        """
        # Rough approximation: 1 token ≈ 4 characters for English
        estimated_tokens = len(prompt) // 4
        is_valid = estimated_tokens <= max_tokens
        
        result = {
            "is_valid": is_valid,
            "estimated_tokens": estimated_tokens,
            "max_tokens": max_tokens,
            "prompt_length": len(prompt),
            "warning": None
        }
        
        if not is_valid:
            result["warning"] = f"Prompt may exceed Whisper's token limit ({estimated_tokens} > {max_tokens}). Consider using fewer terms."
            logger.warning(result["warning"])
        
        return result


# Singleton instance for easy access
_vocabulary_instance = None

def get_medical_vocabulary() -> MedicalVocabulary:
    """
    Get singleton instance of MedicalVocabulary
    
    Returns:
        MedicalVocabulary: Shared vocabulary manager instance
    """
    global _vocabulary_instance
    if _vocabulary_instance is None:
        _vocabulary_instance = MedicalVocabulary()
    return _vocabulary_instance


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("\n🔍 Testing Medical Vocabulary Manager\n")
    
    vocab = MedicalVocabulary()
    
    # Print specialty summary
    vocab.print_specialty_summary()
    
    # Test prosthodontics prompt
    print("\n📋 Prosthodontics Prompt (first 300 chars):")
    print("="*60)
    prostho_prompt = vocab.get_prosthodontics_prompt()
    print(prostho_prompt[:300] + "...")
    
    # Validate prompt length
    print("\n✅ Prompt Validation:")
    print("="*60)
    validation = vocab.validate_prompt_length(prostho_prompt)
    print(f"Valid: {validation['is_valid']}")
    print(f"Estimated Tokens: {validation['estimated_tokens']} / {validation['max_tokens']}")
    print(f"Prompt Length: {validation['prompt_length']} characters")
    if validation['warning']:
        print(f"⚠️ Warning: {validation['warning']}")
    
    # Test custom prompt
    print("\n🔧 Custom Prompt Example:")
    print("="*60)
    custom_terms = ["Dr. Smith", "Dr. Johnson", "BioHorizons implant", "Nobel Biocare"]
    custom_prompt = vocab.get_custom_prompt(custom_terms)
    print(f"Added {len(custom_terms)} custom terms")
    print(f"Custom prompt preview: {custom_prompt[:200]}...")
    
    print("\n" + "="*60 + "\n")
