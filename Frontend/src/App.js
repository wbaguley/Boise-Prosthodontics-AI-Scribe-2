import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import RecordingScreen from './components/RecordingScreen';
import SessionDetail from './components/SessionDetail';
import SessionHistory from './components/SessionHistory';

const App = () => {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  const navigate = (view, sessionId = null) => {
    setCurrentView(view);
    setSelectedSessionId(sessionId);
  };

  return (
    <div className="App">
      {currentView === 'dashboard' && <Dashboard onNavigate={navigate} />}
      {currentView === 'recording' && <RecordingScreen onNavigate={navigate} />}
      {currentView === 'session-detail' && <SessionDetail sessionId={selectedSessionId} onNavigate={navigate} />}
      {currentView === 'session-history' && <SessionHistory onNavigate={navigate} />}
    </div>
  );
};

export default App;