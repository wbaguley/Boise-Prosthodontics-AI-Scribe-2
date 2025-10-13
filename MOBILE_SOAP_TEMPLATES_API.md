# 📱 Mobile SOAP Templates API Guide

## 🌐 **Mobile Access Setup**

Your SOAP template management is fully accessible on mobile devices through the existing API endpoints via ngrok.

### **Base URL (Mobile Access):**
```
https://your-ngrok-url.ngrok-free.app
```
Replace with your actual ngrok URL when running: `ngrok http 3050`

---

## 📋 **SOAP Template API Endpoints**

### **1. List All Templates**
```http
GET /api/templates/list
```
**Response:**
```json
[
  {
    "id": "new_patient_consultation",
    "name": "New Patient Consultation",
    "description": "Template for new patient consultations"
  },
  {
    "id": "treatment_consultation", 
    "name": "Treatment Consultation",
    "description": "Template for treatment planning visits"
  }
]
```

### **2. Get Specific Template**
```http
GET /api/templates/{template_id}
```
**Example:** `GET /api/templates/new_patient_consultation`

**Response:**
```json
{
  "id": "new_patient_consultation",
  "name": "New Patient Consultation", 
  "description": "Template for new patient consultations",
  "ai_instructions": "Focus on comprehensive evaluation...",
  "sections": {
    "Subjective": "Chief complaint and history",
    "Objective": "Clinical findings and examination",
    "Assessment": "Diagnosis and treatment planning",
    "Plan": "Recommended treatment and follow-up"
  }
}
```

### **3. Create New Template**
```http
POST /api/templates
Content-Type: application/json

{
  "id": "emergency_visit",
  "name": "Emergency Visit",
  "description": "Template for emergency dental visits",
  "ai_instructions": "Focus on immediate concerns and pain management",
  "sections": {
    "Subjective": "Chief complaint and pain assessment",
    "Objective": "Emergency examination findings", 
    "Assessment": "Emergency diagnosis",
    "Plan": "Immediate treatment and follow-up"
  }
}
```

### **4. Update Template**
```http
PUT /api/templates/{template_id}
Content-Type: application/json

{
  "name": "Updated Template Name",
  "description": "Updated description",
  "ai_instructions": "Updated AI instructions",
  "sections": {
    "Subjective": "Updated subjective section",
    "Objective": "Updated objective section",
    "Assessment": "Updated assessment section", 
    "Plan": "Updated plan section"
  }
}
```

### **5. Delete Template**
```http
DELETE /api/templates/{template_id}
```

---

## 📱 **Mobile Testing Examples**

### **Using curl (Terminal/Command Line):**

**List templates:**
```bash
curl -X GET "https://your-ngrok-url.ngrok-free.app/api/templates/list"
```

**Get specific template:**
```bash
curl -X GET "https://your-ngrok-url.ngrok-free.app/api/templates/new_patient_consultation"
```

**Create new template:**
```bash
curl -X POST "https://your-ngrok-url.ngrok-free.app/api/templates" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "follow_up_visit",
    "name": "Follow-up Visit",
    "description": "Template for follow-up appointments",
    "ai_instructions": "Focus on treatment progress and next steps",
    "sections": {
      "Subjective": "Treatment response and patient feedback",
      "Objective": "Progress examination",
      "Assessment": "Treatment evaluation",
      "Plan": "Next steps and adjustments"
    }
  }'
```

### **Using Mobile Browser:**

1. **Access the web interface:** `https://your-ngrok-url.ngrok-free.app`
2. **Navigate to Settings → SOAP Templates**
3. **Use the existing template editor** (mobile-responsive)

---

## 🛠 **Mobile App Integration**

If you're building a custom mobile app, use these endpoints:

### **React Native / Flutter / Native Apps:**

```javascript
// Base configuration
const BASE_URL = 'https://your-ngrok-url.ngrok-free.app';

// Fetch templates
async function getTemplates() {
  const response = await fetch(`${BASE_URL}/api/templates/list`);
  return await response.json();
}

// Create template
async function createTemplate(templateData) {
  const response = await fetch(`${BASE_URL}/api/templates`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(templateData)
  });
  return await response.json();
}

// Update template
async function updateTemplate(templateId, templateData) {
  const response = await fetch(`${BASE_URL}/api/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(templateData)
  });
  return await response.json();
}

// Delete template
async function deleteTemplate(templateId) {
  const response = await fetch(`${BASE_URL}/api/templates/${templateId}`, {
    method: 'DELETE'
  });
  return response.ok;
}
```

---

## ✅ **Quick Mobile Setup Steps**

1. **Start your services:** `docker-compose up -d`
2. **Start ngrok:** `ngrok http 3050`  
3. **Use your ngrok URL** in mobile apps/browsers
4. **Access templates via API** or web interface

### **Mobile Browser Access:**
- Open `https://your-ngrok-url.ngrok-free.app` 
- Login/navigate to Settings → SOAP Templates
- Full mobile-responsive interface available

### **API Access:**
- Use endpoints documented above
- All CRUD operations supported
- JSON format for all requests/responses

---

## 🔒 **Security Notes**

- ngrok URLs are temporary and change each restart
- For production, use a permanent domain with SSL
- Consider adding authentication headers if needed
- All existing security measures are preserved

---

## 📞 **Support**

The mobile API access maintains full compatibility with the web application. All template changes made via mobile will be immediately available in the web interface and vice versa.

**Current Templates Location:**
- `Backend/soap_templates/` directory
- Automatically synced across all interfaces