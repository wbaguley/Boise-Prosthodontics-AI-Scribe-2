import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '';

/**
 * StatusBar component showing real-time system health
 * Displays backend, Dentrix, LLM, and Whisper status
 */
const StatusBar = ({ position = 'bottom' }) => {
  const [backendStatus, setBackendStatus] = useState('checking'); // 'online', 'offline', 'checking'
  const [dentrixStatus, setDentrixStatus] = useState('checking'); // 'connected', 'disconnected', 'not-configured', 'checking'
  const [llmStatus, setLlmStatus] = useState('checking'); // 'ready', 'processing', 'error', 'checking'
  const [whisperStatus, setWhisperStatus] = useState('checking'); // 'loaded', 'loading', 'error', 'checking'
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [details, setDetails] = useState({});

  // Check status on mount and every 30 seconds
  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, []);

  const checkStatus = async () => {
    try {
      // Check backend health
      const backendResponse = await fetch(`${API_URL}/api/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      }).catch(() => ({ ok: false }));

      if (backendResponse.ok) {
        const backendData = await backendResponse.json();
        setBackendStatus('online');
        
        // Extract status from health check response
        setLlmStatus(backendData.llm_status || 'ready');
        setWhisperStatus(backendData.whisper_status || 'loaded');
        
        setDetails(prev => ({
          ...prev,
          backend: backendData
        }));
      } else {
        setBackendStatus('offline');
        setLlmStatus('error');
        setWhisperStatus('error');
      }

      // Check Dentrix health if backend is online
      if (backendResponse.ok) {
        const dentrixResponse = await fetch(`${API_URL}/api/dentrix/health`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        }).catch(() => ({ ok: false }));

        if (dentrixResponse.ok) {
          const dentrixData = await dentrixResponse.json();
          setDentrixStatus(dentrixData.status === 'healthy' ? 'connected' : 'disconnected');
          
          setDetails(prev => ({
            ...prev,
            dentrix: dentrixData
          }));
        } else {
          setDentrixStatus('not-configured');
        }
      } else {
        setDentrixStatus('not-configured');
      }

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Status check error:', error);
      setBackendStatus('offline');
      setDentrixStatus('not-configured');
      setLlmStatus('error');
      setWhisperStatus('error');
      setLastUpdated(new Date());
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
      case 'connected':
      case 'ready':
      case 'loaded':
        return 'bg-green-500';
      case 'processing':
      case 'loading':
      case 'checking':
        return 'bg-yellow-500 animate-pulse';
      case 'disconnected':
      case 'not-configured':
        return 'bg-gray-400';
      case 'offline':
      case 'error':
      default:
        return 'bg-red-500';
    }
  };

  const getStatusText = (service, status) => {
    const statusMap = {
      backend: {
        online: 'Backend Online',
        offline: 'Backend Offline',
        checking: 'Checking...'
      },
      dentrix: {
        connected: 'Dentrix Connected',
        disconnected: 'Dentrix Disconnected',
        'not-configured': 'Dentrix Not Configured',
        checking: 'Checking...'
      },
      llm: {
        ready: 'LLM Ready',
        processing: 'LLM Processing',
        error: 'LLM Error',
        checking: 'Checking...'
      },
      whisper: {
        loaded: 'Whisper Loaded',
        loading: 'Whisper Loading',
        error: 'Whisper Error',
        checking: 'Checking...'
      }
    };

    return statusMap[service]?.[status] || status;
  };

  const getTooltip = (service, status) => {
    const tooltips = {
      backend: {
        online: 'Backend API is responding normally',
        offline: 'Cannot connect to backend server',
        checking: 'Checking backend connection...'
      },
      dentrix: {
        connected: 'Dentrix bridge is connected and responding',
        disconnected: 'Dentrix bridge is not responding',
        'not-configured': 'Dentrix integration is not enabled',
        checking: 'Checking Dentrix connection...'
      },
      llm: {
        ready: 'Language model is ready to process requests',
        processing: 'Language model is currently processing',
        error: 'Language model encountered an error',
        checking: 'Checking LLM status...'
      },
      whisper: {
        loaded: 'Whisper model is loaded and ready',
        loading: 'Whisper model is loading...',
        error: 'Whisper model failed to load',
        checking: 'Checking Whisper status...'
      }
    };

    return tooltips[service]?.[status] || 'Unknown status';
  };

  const positionClasses = position === 'bottom'
    ? 'fixed bottom-0 left-0 right-0'
    : 'fixed top-0 right-0';

  return (
    <>
      <div className={`${positionClasses} bg-white border-t border-gray-200 shadow-lg z-40`}>
        <div className="max-w-7xl mx-auto px-4 py-2">
          <div className="flex items-center justify-between">
            {/* Status Indicators */}
            <div className="flex items-center gap-6">
              {/* Backend Status */}
              <div className="flex items-center gap-2 group relative">
                <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(backendStatus)}`}></div>
                <span className="text-xs font-medium text-gray-700">
                  {getStatusText('backend', backendStatus)}
                </span>
                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
                  {getTooltip('backend', backendStatus)}
                </div>
              </div>

              {/* Dentrix Status */}
              <div className="flex items-center gap-2 group relative">
                <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(dentrixStatus)}`}></div>
                <span className="text-xs font-medium text-gray-700">
                  {getStatusText('dentrix', dentrixStatus)}
                </span>
                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-50">
                  {getTooltip('dentrix', dentrixStatus)}
                </div>
              </div>

              {/* LLM Status */}
              <div className="flex items-center gap-2 group relative">
                <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(llmStatus)}`}></div>
                <span className="text-xs font-medium text-gray-700">
                  {getStatusText('llm', llmStatus)}
                </span>
                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-50">
                  {getTooltip('llm', llmStatus)}
                </div>
              </div>

              {/* Whisper Status */}
              <div className="flex items-center gap-2 group relative">
                <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(whisperStatus)}`}></div>
                <span className="text-xs font-medium text-gray-700">
                  {getStatusText('whisper', whisperStatus)}
                </span>
                <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap z-50">
                  {getTooltip('whisper', whisperStatus)}
                </div>
              </div>
            </div>

            {/* Last Updated & Details Button */}
            <div className="flex items-center gap-4">
              {lastUpdated && (
                <span className="text-xs text-gray-500">
                  Updated {lastUpdated.toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                {showDetails ? 'Hide Details' : 'Show Details'}
              </button>
              <button
                onClick={checkStatus}
                className="text-xs text-gray-600 hover:text-gray-800 font-medium"
                title="Refresh status"
              >
                🔄 Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Details Modal */}
      {showDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-800">System Status Details</h2>
                <button
                  onClick={() => setShowDetails(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Backend Details */}
              <div>
                <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(backendStatus)}`}></div>
                  Backend API
                </h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-xs text-gray-700 overflow-auto">
                    {JSON.stringify(details.backend || { status: backendStatus }, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Dentrix Details */}
              <div>
                <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(dentrixStatus)}`}></div>
                  Dentrix Integration
                </h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="text-xs text-gray-700 overflow-auto">
                    {JSON.stringify(details.dentrix || { status: dentrixStatus }, null, 2)}
                  </pre>
                </div>
              </div>

              {/* LLM & Whisper Details */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(llmStatus)}`}></div>
                    LLM Status
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-700">{llmStatus}</p>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${getStatusColor(whisperStatus)}`}></div>
                    Whisper Status
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-700">{whisperStatus}</p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={checkStatus}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  Refresh Status
                </button>
                <button
                  onClick={() => setShowDetails(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default StatusBar;
