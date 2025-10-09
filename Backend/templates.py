import json
from pathlib import Path

class TemplateManager:
    def __init__(self):
        self.templates_dir = Path("soap_templates")
        self.templates_dir.mkdir(exist_ok=True)
        # Removed automatic default template creation - templates are now created only through the app
        
    def create_default_templates_DISABLED(self):
        """Create default SOAP templates if they don't exist"""
        
        # Work Up Template
        work_up_template = {
            "name": "Work Up",
            "description": "Comprehensive patient workup and examination",
            "ai_instructions": "Focus on thorough documentation of patient history, comprehensive examination findings, and detailed treatment planning. Use proper dental terminology and tooth numbering (1-32). Include relevant medical history that may impact dental treatment.",
            "sections": {
                "SUBJECTIVE": [
                    "Chief Complaint",
                    "History of Present Illness",
                    "Dental History",
                    "Medical History",
                    "Current Medications",
                    "Allergies"
                ],
                "OBJECTIVE": [
                    "Extraoral Exam",
                    "Intraoral Exam",
                    "Existing Restorations",
                    "Periodontal Status",
                    "Radiographic Findings",
                    "Occlusion Analysis"
                ],
                "ASSESSMENT": [
                    "Primary Diagnosis",
                    "Secondary Findings",
                    "Prognosis"
                ],
                "PLAN": [
                    "Immediate Treatment",
                    "Definitive Treatment",
                    "Alternative Options",
                    "Follow-up Schedule"
                ]
            }
        }
        
        # Treatment Consultation Template
        treatment_consult_template = {
            "name": "Treatment Consultation",
            "description": "Consultation focused on treatment planning and patient education",
            "ai_instructions": "Emphasize patient education, treatment options discussion, and informed consent process. Document patient's understanding and concerns. Focus on clear communication of benefits, risks, and alternatives.",
            "sections": {
                "SUBJECTIVE": [
                    "Patient's Understanding",
                    "Treatment Goals",
                    "Concerns/Questions"
                ],
                "OBJECTIVE": [
                    "Treatment Options Discussed",
                    "Benefits and Risks",
                    "Time Requirements",
                    "Financial Considerations"
                ],
                "ASSESSMENT": [
                    "Patient's Decision",
                    "Readiness for Treatment"
                ],
                "PLAN": [
                    "Selected Treatment",
                    "Preparation Requirements",
                    "Next Appointment",
                    "Pre-treatment Instructions"
                ]
            }
        }
        
        # New Patient Consultation Template  
        new_patient_template = {
            "name": "New Patient Consultation",
            "description": "Initial consultation and comprehensive evaluation for new patients",
            "ai_instructions": "Document thorough initial assessment for new patients. Focus on establishing baseline health status, identifying immediate concerns, and creating comprehensive treatment priorities. Include patient's dental anxiety level and previous experiences.",
            "sections": {
                "SUBJECTIVE": [
                    "Chief Complaint",
                    "Previous Dental Experiences",
                    "Expectations"
                ],
                "OBJECTIVE": [
                    "Comprehensive Exam Findings",
                    "Radiographic Review",
                    "Photographs Taken"
                ],
                "ASSESSMENT": [
                    "Overall Dental Health",
                    "Risk Assessment",
                    "Treatment Priorities"
                ],
                "PLAN": [
                    "Recommended Workup",
                    "Immediate Needs",
                    "Long-term Treatment Plan"
                ]
            }
        }
        
        # Save default templates
        if not (self.templates_dir / "work_up.json").exists():
            self.save_template("work_up", work_up_template)
        if not (self.templates_dir / "treatment_consultation.json").exists():
            self.save_template("treatment_consultation", treatment_consult_template)
        if not (self.templates_dir / "new_patient.json").exists():
            self.save_template("new_patient", new_patient_template)
    
    def save_template(self, name, template):
        """Save SOAP template"""
        template_path = self.templates_dir / f"{name}.json"
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=2)
    
    def get_templates(self):
        """Get all available templates"""
        templates = {}
        for file in self.templates_dir.glob("*.json"):
            with open(file, 'r') as f:
                templates[file.stem] = json.load(f)
        return templates
    
    def get_template(self, name):
        """Get specific template"""
        template_path = self.templates_dir / f"{name}.json"
        if template_path.exists():
            with open(template_path, 'r') as f:
                return json.load(f)
        return None
    
    def create_custom_template(self, template_id, name, description, ai_instructions, sections):
        """Create a new custom template"""
        template = {
            "name": name,
            "description": description,
            "ai_instructions": ai_instructions,
            "sections": sections,
            "custom": True,
            "created_at": str(Path().resolve())  # Simple timestamp
        }
        self.save_template(template_id, template)
        return template
    
    def update_template(self, template_id, name=None, description=None, ai_instructions=None, sections=None):
        """Update an existing template"""
        print(f"TemplateManager: Updating template {template_id}")
        print(f"Parameters - name: {name}, description: {description}")
        print(f"AI instructions length: {len(ai_instructions) if ai_instructions else 'None'}")
        print(f"Sections parameter type: {type(sections)}")
        print(f"Sections parameter value: {sections}")
        
        template = self.get_template(template_id)
        if not template:
            print(f"Template {template_id} not found")
            return None
        
        print(f"Existing template sections before update: {template.get('sections', {})}")
        
        # Only update fields that are explicitly provided and not None
        if name is not None:
            template["name"] = name
        if description is not None:
            template["description"] = description  
        if ai_instructions is not None:
            template["ai_instructions"] = ai_instructions
        if sections is not None:
            print(f"Updating sections from {template.get('sections', {})} to {sections}")
            template["sections"] = sections
        else:
            print("Sections parameter is None, keeping existing sections")
            
        print(f"Template sections after update: {template.get('sections', {})}")
        
        self.save_template(template_id, template)
        
        # Verify the template was saved correctly
        saved_template = self.get_template(template_id)
        print(f"Template after saving: {saved_template}")
        
        return template
    
    def delete_template(self, template_id):
        """Delete a custom template (prevent deletion of default templates)"""
        template = self.get_template(template_id)
        if template and template.get("custom", False):
            template_path = self.templates_dir / f"{template_id}.json"
            template_path.unlink(missing_ok=True)
            return True
        return False
    
    def get_template_list(self):
        """Get a list of all templates with basic info"""
        templates = []
        for file in self.templates_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    template = json.load(f)
                    templates.append({
                        "id": file.stem,
                        "name": template.get("name", file.stem),
                        "description": template.get("description", ""),
                        "custom": template.get("custom", False)
                    })
            except Exception as e:
                print(f"Error reading template {file}: {e}")
        return templates