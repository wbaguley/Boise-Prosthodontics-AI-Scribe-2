import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3050';

const SimpleTemplateEditor = ({ templateId, onClose }) => {
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Load template data
  useEffect(() => {
    if (templateId) {
      loadTemplate();
    }
  }, [templateId]);

  const loadTemplate = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/templates/${templateId}?_t=${Date.now()}`);
      if (response.ok) {
        const data = await response.json();
        setTemplate(data);
        console.log('Loaded template:', data);
      } else {
        alert('Failed to load template');
        onClose();
      }
    } catch (error) {
      console.error('Error loading template:', error);
      alert('Error loading template');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  // Save template immediately when field changes
  const saveField = async (field, value) => {
    if (!template) return;
    
    try {
      setSaving(true);
      const updateData = {
        name: template.name,
        description: template.description,
        ai_instructions: template.ai_instructions,
        sections: template.sections,
        [field]: value
      };

      console.log('Saving field:', field, 'with value:', value);
      
      const response = await fetch(`${API_URL}/api/templates/${templateId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        const updatedTemplate = await response.json();
        setTemplate(updatedTemplate.template);
        console.log('Field saved successfully:', field);
      } else {
        const error = await response.json();
        alert(`Failed to save: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error saving field:', error);
      alert('Error saving changes');
    } finally {
      setSaving(false);
    }
  };

  // Add section item
  const addSectionItem = async (sectionName) => {
    const newItem = prompt(`Add new ${sectionName} item:`);
    if (!newItem || !newItem.trim()) return;

    const updatedSections = {
      ...template.sections,
      [sectionName]: [...template.sections[sectionName], newItem.trim()]
    };

    await saveField('sections', updatedSections);
  };

  // Remove section item
  const removeSectionItem = async (sectionName, index) => {
    const updatedSections = {
      ...template.sections,
      [sectionName]: template.sections[sectionName].filter((_, i) => i !== index)
    };

    await saveField('sections', updatedSections);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white p-6 rounded-lg">
          <div className="text-center">Loading template...</div>
        </div>
      </div>
    );
  }

  if (!template) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Edit Template: {template.name}</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          {saving && (
            <div className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded mb-4">
              Saving changes...
            </div>
          )}

          {/* Template Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Template Name
            </label>
            <input
              type="text"
              value={template.name || ''}
              onChange={(e) => {
                const newTemplate = { ...template, name: e.target.value };
                setTemplate(newTemplate);
              }}
              onBlur={(e) => saveField('name', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Description */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={template.description || ''}
              onChange={(e) => {
                const newTemplate = { ...template, description: e.target.value };
                setTemplate(newTemplate);
              }}
              onBlur={(e) => saveField('description', e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* AI Instructions */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AI Instructions
            </label>
            <textarea
              value={template.ai_instructions || ''}
              onChange={(e) => {
                const newTemplate = { ...template, ai_instructions: e.target.value };
                setTemplate(newTemplate);
              }}
              onBlur={(e) => saveField('ai_instructions', e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Instructions for the AI on how to use this template..."
            />
          </div>

          {/* SOAP Template Structure */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4">SOAP Template Structure</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {Object.entries(template.sections || {}).map(([sectionName, items]) => (
                <div key={sectionName} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-medium text-gray-900">{sectionName}</h4>
                    <button
                      onClick={() => addSectionItem(sectionName)}
                      className="text-sm bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
                    >
                      + Add Item
                    </button>
                  </div>
                  <div className="space-y-2">
                    {items && items.length > 0 ? (
                      items.map((item, index) => (
                        <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                          <span className="text-sm">{item}</span>
                          <button
                            onClick={() => removeSectionItem(sectionName, index)}
                            className="text-red-500 hover:text-red-700 text-sm"
                          >
                            Remove
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="text-gray-500 text-sm italic">
                        No items yet. Click "Add Item" to add elements for this section.
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Close Button */}
          <div className="flex justify-end pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleTemplateEditor;