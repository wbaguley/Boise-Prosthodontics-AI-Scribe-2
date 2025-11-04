import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, DollarSign, Zap, Cloud, Server, Trash2 } from 'lucide-react';

const Settings = ({ onSave }) => {
  const [currentProvider, setCurrentProvider] = useState('ollama');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [openaiModel, setOpenaiModel] = useState('gpt-4o-mini');
  const [ollamaModel, setOllamaModel] = useState('llama3.1:8b');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [apiKeySaved, setApiKeySaved] = useState(false); // Track if API key was saved

  useEffect(() => {
    loadCurrentSettings();
  }, []);

  const loadCurrentSettings = async () => {
    try {
      const response = await fetch('/api/llm/config');
      const data = await response.json();
      
      if (data.success) {
        setCurrentProvider(data.llm_provider || 'ollama');
        
        if (data.llm_provider === 'openai') {
          setOpenaiModel(data.model || 'gpt-4o-mini');
          setApiKeySaved(data.has_api_key || false); // Check if API key is configured
        } else {
          setOllamaModel(data.model || 'llama3.1:8b');
        }
      }
    } catch (err) {
      console.error('Error loading settings:', err);
      setError('Failed to load current settings');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    setError('');
    setMessage('');

    // Validation - only require API key if it hasn't been saved before and we're using OpenAI
    if (currentProvider === 'openai' && !openaiApiKey && !apiKeySaved) {
      setError('OpenAI API key is required when using OpenAI provider');
      setSaving(false);
      return;
    }

    try {
      const config = {
        provider: currentProvider,
        openai_api_key: currentProvider === 'openai' ? openaiApiKey : undefined,
        openai_model: currentProvider === 'openai' ? openaiModel : undefined,
        ollama_model: currentProvider === 'ollama' ? ollamaModel : undefined,
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
        setMessage('Settings saved successfully! The system will use the new configuration immediately.');
        
        // Mark API key as saved if we're using OpenAI
        if (currentProvider === 'openai') {
          setApiKeySaved(true);
          setOpenaiApiKey(''); // Clear from display for security
        }
        
        // Notify parent component (Dashboard) to refresh
        if (onSave) {
          setTimeout(() => onSave(), 1000); // Close modal after 1 second
        }
      } else {
        setError(data.detail || 'Failed to save settings');
      }
    } catch (err) {
      setError('Error saving settings: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const deleteApiKey = async () => {
    if (!window.confirm('Are you sure you want to delete your OpenAI API key? This will switch you back to the free Ollama provider.')) {
      return;
    }

    setDeleting(true);
    setError('');
    setMessage('');

    try {
      const response = await fetch('/api/llm/config/api-key', {
        method: 'DELETE',
      });

      const data = await response.json();
      
      if (data.success) {
        setMessage('API key deleted successfully. Switched to Ollama provider.');
        setApiKeySaved(false);
        setOpenaiApiKey('');
        setCurrentProvider('ollama');
        setTimeout(() => setMessage(''), 5000);
      } else {
        setError(data.detail || 'Failed to delete API key');
      }
    } catch (err) {
      setError('Error deleting API key: ' + err.message);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-600">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <SettingsIcon className="w-8 h-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-800">LLM Provider Settings</h1>
      </div>

      {message && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800">{message}</p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Provider Selection */}
      <div className="bg-white shadow-lg rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-600" />
          Choose Your AI Provider
        </h2>

        <div className="space-y-4">
          {/* Ollama Option */}
          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              currentProvider === 'ollama'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setCurrentProvider('ollama')}
          >
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="provider"
                value="ollama"
                checked={currentProvider === 'ollama'}
                onChange={(e) => setCurrentProvider(e.target.value)}
                className="mt-1"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Server className="w-5 h-5 text-green-600" />
                  <h3 className="font-semibold text-lg">Ollama (Local - Free)</h3>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-semibold">
                    FREE
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-2">
                  Run AI models locally on your own hardware. Private, secure, and no per-use costs.
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>✅ Completely free - no API costs</li>
                  <li>✅ 100% private - data stays on your server</li>
                  <li>✅ No internet required for AI processing</li>
                  <li>⚠️ Requires GPU for best performance</li>
                </ul>
                
                {currentProvider === 'ollama' && (
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Ollama Model
                    </label>
                    <select
                      value={ollamaModel}
                      onChange={(e) => setOllamaModel(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="llama3.1:8b">Llama 3.1 8B (Recommended)</option>
                      <option value="codellama:13b">Code Llama 13B</option>
                      <option value="mixtral:8x7b">Mixtral 8x7B</option>
                      <option value="meditron:7b">Meditron 7B (Medical)</option>
                    </select>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* OpenAI Option */}
          <div
            className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
              currentProvider === 'openai'
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setCurrentProvider('openai')}
          >
            <div className="flex items-start gap-3">
              <input
                type="radio"
                name="provider"
                value="openai"
                checked={currentProvider === 'openai'}
                onChange={(e) => setCurrentProvider(e.target.value)}
                className="mt-1"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Cloud className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold text-lg">OpenAI (Cloud - Paid)</h3>
                  <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full font-semibold">
                    PAY PER USE
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-2">
                  Use OpenAI's GPT models in the cloud. Fast, powerful, and requires no local resources.
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>✅ Latest GPT-4 models available</li>
                  <li>✅ No local GPU required</li>
                  <li>✅ Extremely fast response times</li>
                  <li>⚠️ Costs ~$0.15 per 1M tokens</li>
                  <li>⚠️ Requires internet connection</li>
                </ul>

                {currentProvider === 'openai' && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-gray-700">
                          OpenAI API Key {apiKeySaved && <span className="text-green-600 ml-2">✓ Saved</span>}
                        </label>
                        {apiKeySaved && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteApiKey();
                            }}
                            disabled={deleting}
                            className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                          >
                            <Trash2 className="w-3 h-3" />
                            {deleting ? 'Deleting...' : 'Delete Key'}
                          </button>
                        )}
                      </div>
                      <input
                        type="password"
                        value={openaiApiKey}
                        onChange={(e) => setOpenaiApiKey(e.target.value)}
                        placeholder={apiKeySaved ? "••••••••••••••••" : "sk-proj-..."}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        {apiKeySaved ? (
                          "✓ API key is encrypted and stored securely. Leave blank to keep current key."
                        ) : (
                          <>
                            Get your API key from{' '}
                            <a
                              href="https://platform.openai.com/api-keys"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-purple-600 hover:underline"
                            >
                              OpenAI Platform
                            </a>
                          </>
                        )}
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Model Selection
                      </label>
                      <select
                        value={openaiModel}
                        onChange={(e) => setOpenaiModel(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      >
                        <optgroup label="GPT-4o Series (Latest - Best for Medical)">
                          <option value="gpt-4o-mini">GPT-4o Mini (Recommended - Fast & Cheap)</option>
                          <option value="gpt-4o">GPT-4o (Balanced)</option>
                        </optgroup>
                        <optgroup label="GPT-4 Turbo Series (Most Powerful)">
                          <option value="gpt-4-turbo">GPT-4 Turbo (Most Powerful)</option>
                          <option value="gpt-4-turbo-preview">GPT-4 Turbo Preview</option>
                        </optgroup>
                        <optgroup label="GPT-4 Series (Legacy)">
                          <option value="gpt-4">GPT-4 (Original)</option>
                          <option value="gpt-4-0613">GPT-4 (June 2023)</option>
                        </optgroup>
                        <optgroup label="GPT-3.5 Series (Budget Option)">
                          <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Cheapest)</option>
                          <option value="gpt-3.5-turbo-16k">GPT-3.5 Turbo 16K (Longer context)</option>
                        </optgroup>
                      </select>
                      <p className="mt-1 text-xs text-gray-500">
                        {openaiModel === 'gpt-4o-mini' && '~$0.15 per 1M input tokens, $0.60 per 1M output tokens'}
                        {openaiModel === 'gpt-4o' && '~$5.00 per 1M input tokens, $15.00 per 1M output tokens'}
                        {openaiModel === 'gpt-4-turbo' && '~$10.00 per 1M input tokens, $30.00 per 1M output tokens'}
                        {openaiModel === 'gpt-4' && '~$30.00 per 1M input tokens, $60.00 per 1M output tokens'}
                        {openaiModel === 'gpt-3.5-turbo' && '~$0.50 per 1M input tokens, $1.50 per 1M output tokens'}
                        {!['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'].includes(openaiModel) && 'Pricing varies by model'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Comparison Table */}
      <div className="bg-white shadow-lg rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-green-600" />
          Cost Comparison
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left p-3 font-semibold">Feature</th>
                <th className="text-left p-3 font-semibold">Ollama (Local)</th>
                <th className="text-left p-3 font-semibold">OpenAI (Cloud)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td className="p-3 font-medium">Cost per SOAP Note</td>
                <td className="p-3 text-green-600 font-semibold">$0.00</td>
                <td className="p-3">~$0.001 - $0.01</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Monthly Cost (100 notes)</td>
                <td className="p-3 text-green-600 font-semibold">$0.00</td>
                <td className="p-3">~$0.10 - $1.00</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Setup Requirements</td>
                <td className="p-3">GPU recommended</td>
                <td className="p-3">Just an API key</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Data Privacy</td>
                <td className="p-3 text-green-600 font-semibold">100% Local</td>
                <td className="p-3">Sent to OpenAI</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Internet Required</td>
                <td className="p-3 text-green-600 font-semibold">No</td>
                <td className="p-3">Yes</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Response Speed</td>
                <td className="p-3">Depends on GPU</td>
                <td className="p-3 text-green-600 font-semibold">Very Fast</td>
              </tr>
              <tr>
                <td className="p-3 font-medium">Model Quality</td>
                <td className="p-3">Good</td>
                <td className="p-3 text-green-600 font-semibold">Excellent</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>💡 Recommendation:</strong> Start with Ollama (free) to test the system. 
            Switch to OpenAI if you need faster processing or don't have a GPU.
          </p>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          {currentProvider === 'openai' && !openaiApiKey && !apiKeySaved && (
            <p className="text-orange-600">⚠️ API key required to use OpenAI</p>
          )}
          {currentProvider === 'openai' && apiKeySaved && (
            <p className="text-green-600">✓ OpenAI API key is configured</p>
          )}
        </div>
        <button
          onClick={saveSettings}
          disabled={saving || (currentProvider === 'openai' && !openaiApiKey && !apiKeySaved)}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
            saving || (currentProvider === 'openai' && !openaiApiKey && !apiKeySaved)
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg hover:shadow-xl'
          }`}
        >
          <Save className="w-5 h-5" />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

export default Settings;
