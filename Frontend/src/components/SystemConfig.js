import React, { useState, useEffect } from 'react';

const SystemConfig = ({ onNavigate }) => {
  const [configs, setConfigs] = useState([]);
  const [timezones, setTimezones] = useState([]);
  const [currentTimezone, setCurrentTimezone] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  
  // LLM Provider state
  const [llmProvider, setLlmProvider] = useState('ollama');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [openaiModel, setOpenaiModel] = useState('gpt-4o-mini');
  const [ollamaModel, setOllamaModel] = useState('llama3.1:8b');
  const [savingLlm, setSavingLlm] = useState(false);

  useEffect(() => {
    loadConfigs();
    loadTimezones();
    loadCurrentTimezone();
    loadLlmConfig();
  }, []);

  const loadConfigs = async () => {
    try {
      const response = await fetch('/api/system-config');
      const data = await response.json();
      if (data.success) {
        setConfigs(data.configs);
      }
    } catch (err) {
      console.error('Error loading configs:', err);
    }
  };

  const loadTimezones = async () => {
    try {
      const response = await fetch('/api/timezones');
      const data = await response.json();
      if (data.success) {
        setTimezones(data.timezones);
      }
    } catch (err) {
      console.error('Error loading timezones:', err);
    }
  };

  const loadCurrentTimezone = async () => {
    try {
      const response = await fetch('/api/timezone/current');
      const data = await response.json();
      if (data.success) {
        setCurrentTimezone(data.timezone);
      }
      setLoading(false);
    } catch (err) {
      console.error('Error loading current timezone:', err);
      setLoading(false);
    }
  };

  const loadLlmConfig = async () => {
    try {
      const response = await fetch('/api/llm/config');
      const data = await response.json();
      if (data.success) {
        setLlmProvider(data.llm_provider || 'ollama');
        setOllamaModel(data.model || 'llama3.1:8b');
        setOpenaiModel(data.model || 'gpt-4o-mini');
      }
    } catch (err) {
      console.error('Error loading LLM config:', err);
    }
  };

  const handleSaveLlmConfig = async () => {
    setSavingLlm(true);
    setError('');
    setMessage('');
    
    try {
      const config = {
        provider: llmProvider,
        openai_api_key: llmProvider === 'openai' ? openaiApiKey : undefined,
        openai_model: llmProvider === 'openai' ? openaiModel : undefined,
        ollama_model: llmProvider === 'ollama' ? ollamaModel : undefined,
      };

      const response = await fetch('/api/llm/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });
      
      const data = await response.json();
      if (data.success) {
        setMessage('LLM configuration updated successfully! Backend will restart to apply changes.');
        setTimeout(() => setMessage(''), 5000);
        loadLlmConfig();
      } else {
        setError(data.detail || 'Failed to update LLM configuration');
      }
    } catch (err) {
      setError('Error updating LLM configuration: ' + err.message);
    } finally {
      setSavingLlm(false);
    }
  };

  const handleTimezoneChange = async (newTimezone) => {
    setSaving(true);
    setError('');
    try {
      const response = await fetch('/api/timezone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ timezone: newTimezone }),
      });
      
      const data = await response.json();
      if (data.success) {
        setCurrentTimezone(newTimezone);
        setMessage('Timezone updated successfully!');
        setTimeout(() => setMessage(''), 3000);
        loadCurrentTimezone(); // Refresh current time display
      } else {
        setError(data.detail || 'Failed to update timezone');
      }
    } catch (err) {
      setError('Error updating timezone: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = async (key, value, description) => {
    try {
      const response = await fetch('/api/system-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ key, value, description }),
      });
      
      const data = await response.json();
      if (data.success) {
        setMessage(`${key} updated successfully!`);
        setTimeout(() => setMessage(''), 3000);
        loadConfigs(); // Refresh configs
      } else {
        setError(data.detail || `Failed to update ${key}`);
      }
    } catch (err) {
      setError(`Error updating ${key}: ` + err.message);
    }
  };

  if (loading) {
    return <div className="p-4">Loading system configuration...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">System Configuration</h1>
        <button
          onClick={() => onNavigate && onNavigate('dashboard')}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center gap-2"
        >
          ← Back to Dashboard
        </button>
      </div>
      
      {message && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 rounded border">
          {message}
        </div>
      )}
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded border">
          {error}
        </div>
      )}

      {/* Timezone Configuration */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Timezone Settings</h2>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Current Timezone: <span className="font-mono text-blue-600">{currentTimezone}</span>
          </label>
          
          <select
            value={currentTimezone}
            onChange={(e) => handleTimezoneChange(e.target.value)}
            disabled={saving}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            {timezones.map((tz) => (
              <option key={tz.name} value={tz.name}>
                {tz.display_name} (Current: {tz.current_time})
              </option>
            ))}
          </select>
          
          {saving && (
            <p className="mt-2 text-sm text-gray-500">Updating timezone...</p>
          )}
        </div>
        
        <div className="text-sm text-gray-600">
          <p>This timezone will be used for:</p>
          <ul className="list-disc list-inside mt-2">
            <li>SOAP note timestamps</li>
            <li>Session recording dates</li>
            <li>Email timestamps</li>
            <li>Report generation</li>
          </ul>
        </div>
      </div>

      {/* Other System Configurations */}
      <div className="bg-white shadow-md rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">General Settings</h2>
        
        <div className="space-y-4">
          {configs.map((config) => (
            <div key={config.key} className="border-b border-gray-200 pb-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-900">
                    {config.key.replace(/_/g, ' ').toUpperCase()}
                  </h3>
                  {config.description && (
                    <p className="text-sm text-gray-500 mt-1">{config.description}</p>
                  )}
                </div>
                <div className="ml-4">
                  <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                    {config.value}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-4 text-sm text-gray-500">
          <p>
            <strong>Note:</strong> Most settings can be modified through the API. 
            Contact your system administrator for advanced configuration changes.
          </p>
        </div>
      </div>
      
      {/* Current Time Display */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
        <h3 className="text-lg font-medium text-blue-800 mb-2">Current System Time</h3>
        <p className="text-blue-700">
          <CurrentTime timezone={currentTimezone} />
        </p>
      </div>
    </div>
  );
};

// Component to show live current time
const CurrentTime = ({ timezone }) => {
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    const updateTime = async () => {
      try {
        const response = await fetch('/api/timezone/current');
        const data = await response.json();
        if (data.success) {
          setCurrentTime(data.formatted_display);
        }
      } catch (err) {
        console.error('Error fetching current time:', err);
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, [timezone]);

  return <span>{currentTime}</span>;
};

export default SystemConfig;