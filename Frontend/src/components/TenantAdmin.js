import React, { useState, useEffect } from 'react';
import { Settings, Save, Upload, Eye, AlertCircle } from 'lucide-react';

/**
 * Tenant Admin Component
 * Allows administrators to configure tenant-specific branding and features
 */
const TenantAdmin = ({ tenantConfig, onClose }) => {
  const [config, setConfig] = useState({
    practice_name: '',
    logo_url: '',
    primary_color: '#3B82F6',
    secondary_color: '#8B5CF6',
    features_enabled: {
      ambient_scribe: true,
      dentrix_integration: true,
      voice_profiles: true,
      openai_option: true,
      email_system: true,
      soap_templates: true
    },
    dentrix_bridge_url: 'http://dentrix_bridge:8001',
    whisper_model: 'medium'
  });

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [previewMode, setPreviewMode] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/config');
      const data = await response.json();
      
      if (data.success) {
        setConfig({
          practice_name: data.practice_name || '',
          logo_url: data.logo_url || '',
          primary_color: data.primary_color || '#3B82F6',
          secondary_color: data.secondary_color || '#8B5CF6',
          features_enabled: data.features_enabled || {},
          dentrix_bridge_url: data.dentrix_bridge_url || 'http://dentrix_bridge:8001',
          whisper_model: data.whisper_model || 'medium'
        });
      }
    } catch (err) {
      console.error('Error loading config:', err);
      setError('Failed to load configuration');
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setError('');
    setMessage('');

    try {
      const response = await fetch(`/api/admin/tenants/${tenantConfig?.tenant_id || 'default'}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      const data = await response.json();
      
      if (data.success) {
        setMessage('Configuration saved successfully! Refresh the page to see changes.');
        setTimeout(() => setMessage(''), 5000);
      } else {
        setError(data.detail || 'Failed to save configuration');
      }
    } catch (err) {
      setError('Error saving configuration: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Convert to base64
    const reader = new FileReader();
    reader.onloadend = () => {
      setConfig({ ...config, logo_url: reader.result });
    };
    reader.readAsDataURL(file);
  };

  const handleFeatureToggle = (feature) => {
    setConfig({
      ...config,
      features_enabled: {
        ...config.features_enabled,
        [feature]: !config.features_enabled[feature]
      }
    });
  };

  const previewChanges = () => {
    // Apply colors to preview
    if (previewMode) {
      // Reset to current
      document.documentElement.style.setProperty('--primary-color', tenantConfig?.primary_color);
      document.documentElement.style.setProperty('--secondary-color', tenantConfig?.secondary_color);
    } else {
      // Apply new colors
      document.documentElement.style.setProperty('--primary-color', config.primary_color);
      document.documentElement.style.setProperty('--secondary-color', config.secondary_color);
    }
    setPreviewMode(!previewMode);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Settings className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-800">Tenant Configuration</h1>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            Close
          </button>
        )}
      </div>

      {/* Messages */}
      {message && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md text-green-800">
          {message}
        </div>
      )}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-800 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* Practice Name */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Practice Information</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Practice Name
              </label>
              <input
                type="text"
                value={config.practice_name}
                onChange={(e) => setConfig({ ...config, practice_name: e.target.value })}
                placeholder="Boise Prosthodontics"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Practice Logo
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleLogoUpload}
                  className="hidden"
                  id="logo-upload"
                />
                <label
                  htmlFor="logo-upload"
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer"
                >
                  <Upload className="w-4 h-4" />
                  Upload Logo
                </label>
                {config.logo_url && (
                  <img
                    src={config.logo_url}
                    alt="Logo preview"
                    className="h-12 object-contain border border-gray-200 rounded"
                  />
                )}
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Recommended: PNG or SVG, max 200px height
              </p>
            </div>
          </div>
        </div>

        {/* Branding Colors */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Branding Colors</h2>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary Color
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={config.primary_color}
                  onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                  className="w-16 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.primary_color}
                  onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="#3B82F6"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Secondary Color
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={config.secondary_color}
                  onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                  className="w-16 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.secondary_color}
                  onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="#8B5CF6"
                />
              </div>
            </div>
          </div>

          <button
            onClick={previewChanges}
            className="mt-4 flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
          >
            <Eye className="w-4 h-4" />
            {previewMode ? 'Stop Preview' : 'Preview Colors'}
          </button>
        </div>

        {/* Feature Toggles */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Enabled Features</h2>
          
          <div className="space-y-3">
            {[
              { key: 'ambient_scribe', label: 'Ambient Scribe', desc: 'Voice recording and transcription' },
              { key: 'dentrix_integration', label: 'Dentrix Integration', desc: 'Send SOAP notes to Dentrix' },
              { key: 'voice_profiles', label: 'Voice Profiles', desc: 'Provider voice identification' },
              { key: 'openai_option', label: 'OpenAI Option', desc: 'Allow OpenAI as LLM provider' },
              { key: 'email_system', label: 'Email System', desc: 'Post-visit email generation' },
              { key: 'soap_templates', label: 'SOAP Templates', desc: 'Customizable SOAP note templates' }
            ].map((feature) => (
              <label key={feature.key} className="flex items-start gap-3 p-3 rounded-md hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.features_enabled[feature.key] || false}
                  onChange={() => handleFeatureToggle(feature.key)}
                  className="mt-1 w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-800">{feature.label}</div>
                  <div className="text-sm text-gray-600">{feature.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Technical Configuration */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Technical Configuration</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dentrix Bridge URL
              </label>
              <input
                type="text"
                value={config.dentrix_bridge_url}
                onChange={(e) => setConfig({ ...config, dentrix_bridge_url: e.target.value })}
                placeholder="http://dentrix_bridge:8001"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Whisper Model Size
              </label>
              <select
                value={config.whisper_model}
                onChange={(e) => setConfig({ ...config, whisper_model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="tiny">Tiny (fastest, least accurate)</option>
                <option value="base">Base</option>
                <option value="small">Small</option>
                <option value="medium">Medium (recommended)</option>
                <option value="large">Large (slowest, most accurate)</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Larger models provide better transcription accuracy but require more resources
              </p>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-3">
          <button
            onClick={saveConfig}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-5 h-5" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TenantAdmin;
