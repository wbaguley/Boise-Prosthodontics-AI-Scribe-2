import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import RecordingScreen from './components/RecordingScreen';
import SessionDetail from './components/SessionDetail';
import SessionHistory from './components/SessionHistory';
import SystemConfig from './components/SystemConfig';

const App = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  const navigate = (view, sessionId = null) => {
    setCurrentView(view);
    setSelectedSessionId(sessionId);
  };

  // Default tenant config (tenant system removed)
  const tenantConfig = {
    tenant_id: 'default',
    practice_name: 'Boise Prosthodontics',
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
    llm_provider: 'ollama',
    whisper_model: 'medium'
  };

  return (
    <div className="App" style={{
      '--primary-color': tenantConfig.primary_color,
      '--secondary-color': tenantConfig.secondary_color
    }}>
      {currentView === 'dashboard' && <Dashboard onNavigate={navigate} tenantConfig={tenantConfig} />}
      {currentView === 'recording' && <RecordingScreen onNavigate={navigate} tenantConfig={tenantConfig} />}
      {currentView === 'session-detail' && <SessionDetail sessionId={selectedSessionId} onNavigate={navigate} tenantConfig={tenantConfig} />}
      {currentView === 'session-history' && <SessionHistory onNavigate={navigate} tenantConfig={tenantConfig} />}
      {currentView === 'system-config' && <SystemConfig onNavigate={navigate} tenantConfig={tenantConfig} />}
    </div>
  );
};

export default App;