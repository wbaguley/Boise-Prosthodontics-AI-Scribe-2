import json
from pathlib import Path

class TemplateManager:
    def __init__(self):
        self.templates_dir = Path("soap_templates")
        self.templates_dir.mkdir(exist_ok=True)
        # Removed automatic default template creation - templates are now created only through the app
        
    def create_default_templates_DISABLED(self):
        """DISABLED: Default templates are no longer created automatically. 
        All templates must be created through the user interface to prevent 
        conflicts and ensure only user-created templates are used."""
        pass
    
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
        """Get specific template - only return user-created templates"""
        # Handle "default" by returning None to force template selection
        if name == "default":
            print(f"Warning: 'default' template requested but no default templates exist. Available templates:")
            available = self.get_template_list()
            for tmpl in available:
                print(f"  - {tmpl['id']}: {tmpl['name']}")
            return None
            
        template_path = self.templates_dir / f"{name}.json"
        if template_path.exists():
            with open(template_path, 'r') as f:
                template_data = json.load(f)
                print(f"✅ Loaded template: {name} -> {template_data.get('name', 'Unknown')}")
                return template_data
        
        print(f"❌ Template not found: {name}")
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