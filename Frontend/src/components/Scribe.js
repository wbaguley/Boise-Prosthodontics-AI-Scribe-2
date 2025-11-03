import React, { useState, useRef, useEffect } from 'react';
import VoiceProfile from './Voiceprofile';
import DentrixIntegration from './DentrixIntegration';

const API_URL = process.env.REACT_APP_API_URL || '';
const getWebSocketURL = () => {
  // Use the same host but ensure we go through the nginx proxy
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  const host = window.location.host;
  
  console.log('WebSocket URL generation - Protocol:', protocol, 'Host:', host);
  
  // If we're in development and connecting to ngrok, use the same host
  // If we're running locally, use localhost:3050 (nginx proxy)
  if (host.includes('ngrok') || host.includes('localhost:3050')) {
    const url = `${protocol}${host}/ws/audio`;
    console.log('Generated WebSocket URL:', url);
    return url;
  } else {
    // Fallback to localhost nginx proxy
    const url = `ws://localhost:3050/ws/audio`;
    console.log('Fallback WebSocket URL:', url);
    return url;
  }
};

const Scribe = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [soapNote, setSoapNote] = useState('');
  const [status, setStatus] = useState('Disconnected');
  const [sessionId, setSessionId] = useState('');
  const [correction, setCorrection] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  
  // Chat functionality for SOAP editing
  const [showEditChat, setShowEditChat] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isProcessingChat, setIsProcessingChat] = useState(false);
  
  // Provider management from API
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [newProviderName, setNewProviderName] = useState('');
  const [newProviderSpecialty, setNewProviderSpecialty] = useState('');
  const [newProviderCredentials, setNewProviderCredentials] = useState('');
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [showVoiceProfile, setShowVoiceProfile] = useState(false);
  
  const [selectedTemplate, setSelectedTemplate] = useState('new_patient_consultation');
  const [availableTemplates, setAvailableTemplates] = useState([]);
  
  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    fetchProviders();
    fetchTemplates();
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/providers`);
      const data = await response.json();
      setProviders(data);
      
      if (data.length > 0 && !selectedProvider) {
        setSelectedProvider(data[0]);
      }
    } catch (error) {
      console.error('Error fetching providers:', error);
      setStatus('Error loading providers');
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_URL}/api/templates`);
      const templates = await response.json();
      setAvailableTemplates(Object.keys(templates));
    } catch (error) {
      console.error('Error fetching templates:', error);
      setAvailableTemplates(['default']);
    }
  };

  const createProvider = async () => {
    if (!newProviderName.trim()) {
      alert('Provider name is required');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/providers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProviderName.trim(),
          specialty: newProviderSpecialty.trim() || null,
          credentials: newProviderCredentials.trim() || null
        })
      });

      if (response.ok) {
        const newProvider = await response.json();
        setProviders([...providers, newProvider]);
        setSelectedProvider(newProvider);
        setNewProviderName('');
        setNewProviderSpecialty('');
        setNewProviderCredentials('');
        setShowProviderModal(false);
        setStatus('Provider added successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create provider');
      }
    } catch (error) {
      console.error('Error creating provider:', error);
      alert('Failed to create provider');
    }
  };

  const deleteProvider = async (providerId) => {
    if (providers.length === 1) {
      alert('Cannot delete the last provider');
      return;
    }

    if (!window.confirm('Are you sure you want to delete this provider?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/providers/${providerId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        const updatedProviders = providers.filter(p => p.id !== providerId);
        setProviders(updatedProviders);
        
        if (selectedProvider?.id === providerId) {
          setSelectedProvider(updatedProviders[0]);
        }
        
        setStatus('Provider deleted successfully');
      } else {
        alert('Failed to delete provider');
      }
    } catch (error) {
      console.error('Error deleting provider:', error);
      alert('Failed to delete provider');
    }
  };

  const connectWebSocket = () => {
    // Prevent multiple connections
    if (websocketRef.current && 
        (websocketRef.current.readyState === WebSocket.CONNECTING || 
         websocketRef.current.readyState === WebSocket.OPEN)) {
      console.log('WebSocket already connected or connecting, skipping...');
      return;
    }

    const wsUrl = getWebSocketURL();
    
    try {
      console.log('Connecting to WebSocket:', wsUrl);
      websocketRef.current = new WebSocket(wsUrl);
      
      websocketRef.current.onopen = () => {
        setConnectionStatus('connected');
        setStatus('Connected - Ready to record');
      };
      
      websocketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.session_id) {
            setSessionId(data.session_id);
          }
          
          if (data.status) {
            setStatus(data.status);
          }
          
          if (data.transcript) {
            setTranscript(data.transcript);
          }
          
          if (data.soap) {
            setSoapNote(data.soap);
          }
          
          if (data.error) {
            setStatus(`Error: ${data.error}`);
            setConnectionStatus('error');
          }
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
      
      websocketRef.current.onerror = (error) => {
        setConnectionStatus('error');
        setStatus('Connection error - check backend');
      };
      
      websocketRef.current.onclose = () => {
        setConnectionStatus('disconnected');
        setStatus('Disconnected - refresh to reconnect');
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setConnectionStatus('error');
    }
  };

  const startRecording = async () => {
    if (!selectedProvider) {
      alert('Please select a provider first');
      return;
    }

    // Connect to WebSocket only when starting recording
    if (!websocketRef.current || 
        (websocketRef.current.readyState !== WebSocket.OPEN && 
         websocketRef.current.readyState !== WebSocket.CONNECTING)) {
      connectWebSocket();
      // Wait a moment for connection to establish
      await new Promise(resolve => setTimeout(resolve, 1000));
    } else if (websocketRef.current.readyState === WebSocket.CONNECTING) {
      // Already connecting, just wait
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      audioChunksRef.current = [];
      
      const mimeType = 'audio/webm;codecs=opus';
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        await sendAudioToBackend(audioBlob);
        
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start(100);
      setIsRecording(true);
      setStatus('Recording... Speak clearly');
      
    } catch (error) {
      console.error('Microphone access error:', error);
      setStatus('Microphone access denied');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('Processing audio...');
    }
  };

  const sendAudioToBackend = async (audioBlob) => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      setStatus('WebSocket not connected');
      return;
    }
    
    try {
      // Send session info first
      websocketRef.current.send(JSON.stringify({
        type: 'session_info',
        doctor: selectedProvider.name,
        template: selectedTemplate
      }));
      
      // Then send audio chunks
      const arrayBuffer = await audioBlob.arrayBuffer();
      const chunkSize = 16384;
      const uint8Array = new Uint8Array(arrayBuffer);
      
      for (let i = 0; i < uint8Array.length; i += chunkSize) {
        const chunk = uint8Array.slice(i, Math.min(i + chunkSize, uint8Array.length));
        websocketRef.current.send(chunk);
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      
      websocketRef.current.send('END');
      
    } catch (error) {
      console.error('Error sending audio:', error);
      setStatus('Failed to send audio');
    }
  };

  const sendCorrection = () => {
    if (correction.trim() && websocketRef.current?.readyState === WebSocket.OPEN) {
      websocketRef.current.send(`CORRECT:${correction}`);
      setCorrection('');
      setStatus('Applying correction...');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      const prevStatus = status;
      setStatus('Copied to clipboard!');
      setTimeout(() => setStatus(prevStatus), 2000);
    });
  };

  // Chat functionality for SOAP note editing
  const sendChatMessage = async () => {
    if (!chatInput.trim() || isProcessingChat || !soapNote) {
      return;
    }

    const userMessage = chatInput.trim();
    setChatInput('');
    setIsProcessingChat(true);

    // Add user message to chat
    const newMessages = [
      ...chatMessages,
      { role: 'user', content: userMessage, timestamp: new Date() }
    ];
    setChatMessages(newMessages);

    try {
      const response = await fetch(`${API_URL}/api/edit-soap-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_soap: soapNote,
          transcript: transcript,
          user_message: userMessage,
          chat_history: chatMessages.slice(-5) // Send last 5 messages for context
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        // Add AI response to chat
        const updatedMessages = [
          ...newMessages,
          { role: 'assistant', content: data.ai_response, timestamp: new Date() }
        ];
        setChatMessages(updatedMessages);

        // Update SOAP note if it was modified
        if (data.updated_soap && data.updated_soap !== soapNote) {
          setSoapNote(data.updated_soap);
          setStatus('SOAP note updated via chat');
        }
      } else {
        const error = await response.text();
        setChatMessages([
          ...newMessages,
          { role: 'assistant', content: `Sorry, I encountered an error: ${error}`, timestamp: new Date() }
        ]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setChatMessages([
        ...newMessages,
        { role: 'assistant', content: 'Sorry, I encountered a connection error. Please try again.', timestamp: new Date() }
      ]);
    } finally {
      setIsProcessingChat(false);
    }
  };

  const clearChat = () => {
    setChatMessages([]);
  };

  // Save chat conversation to AI memory
  const saveChatToMemory = async (messages) => {
    try {
      // Filter out only user messages to check if user contributed
      const userMessages = messages.filter(msg => msg.role === 'user');
      
      if (userMessages.length === 0) {
        // No user messages, don't save
        return;
      }

      // Create a summary of the conversation
      const conversationSummary = messages
        .map(msg => `${msg.role.toUpperCase()}: ${msg.content}`)
        .join('\n\n');

      // Generate a title based on the first user message
      const firstUserMessage = userMessages[0].content.substring(0, 50);
      const title = `Chat Session - Scribe - ${firstUserMessage}...`;

      // Save to AI memory as a knowledge article
      const response = await fetch(`${API_URL}/api/knowledge-articles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          content: conversationSummary,
          category: 'Chat Conversations'
        })
      });

      if (response.ok) {
        console.log('Chat conversation saved to AI memory');
      } else {
        console.error('Failed to save chat to AI memory');
      }
    } catch (error) {
      console.error('Error saving chat to memory:', error);
    }
  };

  const toggleEditChat = async () => {
    if (!soapNote) {
      setStatus('Please generate a SOAP note first before editing');
      return;
    }

    // If we're currently showing the chat and about to close it, save the conversation
    if (showEditChat && chatMessages.length > 0) {
      await saveChatToMemory(chatMessages);
    }

    setShowEditChat(!showEditChat);
    if (!showEditChat && chatMessages.length === 0) {
      // Add welcome message when opening chat for the first time
      setChatMessages([{
        role: 'assistant',
        content: `Hello! I'm here to help you edit your SOAP note. You can ask me to:

• Add missing information
• Modify diagnoses or treatment plans  
• Change wording or terminology
• Add or remove sections
• Update patient information
• Correct any errors

What would you like to change about the SOAP note?`,
        timestamp: new Date()
      }]);
    }
  };

  // Quick action buttons for common edits
  const quickActions = [
    "Add patient's medical history",
    "Update the treatment plan",
    "Add more detail to the assessment", 
    "Include patient's chief complaint",
    "Add follow-up instructions"
  ];

  const sendQuickAction = (action) => {
    if (isProcessingChat) return;
    setChatInput(action);
    // Auto-send after a brief delay to show the user what was selected
    setTimeout(() => {
      if (!isProcessingChat) {
        sendChatMessage();
      }
    }, 100);
  };

  const formatTemplateName = (template) => {
    return template.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const handleVoiceProfileSaved = () => {
    setStatus('Voice profile saved!');
    fetchProviders(); // Refresh to update has_voice_profile status
    setTimeout(() => setStatus('Connected - Ready to record'), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                🦷 Boise Prosthodontics AI Scribe
              </h1>
              <div className="text-sm text-gray-600 flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-green-500' : 
                    connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                  }`}></div>
                  <span>{status}</span>
                </div>
                {sessionId && <span>Session: {sessionId}</span>}
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-auto">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <select
                    value={selectedProvider?.id || ''}
                    onChange={(e) => {
                      const provider = providers.find(p => p.id === parseInt(e.target.value));
                      setSelectedProvider(provider);
                    }}
                    className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                  >
                    {providers.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name} {provider.has_voice_profile ? '🎤' : ''}
                      </option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowProviderModal(true)}
                      className="flex-1 sm:flex-none px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm whitespace-nowrap"
                      title="Manage Providers"
                    >
                      ⚙️ Manage
                    </button>
                    <button
                      onClick={() => setShowVoiceProfile(true)}
                      disabled={!selectedProvider}
                      className="flex-1 sm:flex-none px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 text-sm whitespace-nowrap"
                      title="Train Voice"
                    >
                      🎤 Train
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="w-full sm:w-auto">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  {availableTemplates.map(template => (
                    <option key={template} value={template}>
                      {formatTemplateName(template)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Provider Management Modal */}
        {showProviderModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-[500px] max-h-[90vh] overflow-y-auto">
              <h3 className="text-lg font-semibold mb-4">Manage Providers</h3>
              
              {/* Add New Provider Form */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-3">Add New Provider</h4>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newProviderName}
                    onChange={(e) => setNewProviderName(e.target.value)}
                    placeholder="Provider Name (e.g., Dr. Smith)"
                    className="w-full px-3 py-2 border rounded"
                  />
                  <input
                    type="text"
                    value={newProviderSpecialty}
                    onChange={(e) => setNewProviderSpecialty(e.target.value)}
                    placeholder="Specialty (optional)"
                    className="w-full px-3 py-2 border rounded"
                  />
                  <input
                    type="text"
                    value={newProviderCredentials}
                    onChange={(e) => setNewProviderCredentials(e.target.value)}
                    placeholder="Credentials (optional)"
                    className="w-full px-3 py-2 border rounded"
                  />
                  <button
                    onClick={createProvider}
                    className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    Add Provider
                  </button>
                </div>
              </div>
              
              {/* Provider List */}
              <div className="space-y-2 mb-4">
                <h4 className="font-medium mb-2">Existing Providers</h4>
                {providers.map(provider => (
                  <div key={provider.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <div className="flex-1">
                      <div className="font-medium flex items-center gap-2">
                        {provider.name}
                        {provider.has_voice_profile && <span className="text-green-600">🎤</span>}
                      </div>
                      {provider.specialty && (
                        <div className="text-sm text-gray-600">{provider.specialty}</div>
                      )}
                      {provider.credentials && (
                        <div className="text-xs text-gray-500">{provider.credentials}</div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setSelectedProvider(provider);
                          setShowProviderModal(false);
                          setShowVoiceProfile(true);
                        }}
                        className="text-blue-500 hover:text-blue-700 text-sm px-2"
                      >
                        Voice
                      </button>
                      <button
                        onClick={() => deleteProvider(provider.id)}
                        disabled={providers.length === 1}
                        className="text-red-500 hover:text-red-700 disabled:opacity-50 text-sm px-2"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              
              <button
                onClick={() => setShowProviderModal(false)}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {/* Voice Profile Modal */}
        {showVoiceProfile && selectedProvider && (
          <VoiceProfile
            doctorName={selectedProvider.name}
            onClose={() => setShowVoiceProfile(false)}
            onSave={handleVoiceProfileSaved}
          />
        )}

        {/* Recording Interface */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Recording</h2>
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={connectionStatus !== 'connected' || !selectedProvider}
                className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-all ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600' 
                    : 'bg-blue-500 hover:bg-blue-600'
                } ${connectionStatus !== 'connected' || !selectedProvider ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {isRecording ? '⏹️ Stop Recording' : '🎤 Start Recording'}
              </button>
              
              {selectedProvider?.has_voice_profile && (
                <div className="mt-3 text-sm text-green-600 text-center">
                  ✓ Voice profile active for speaker identification
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Corrections</h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={correction}
                  onChange={(e) => setCorrection(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendCorrection()}
                  placeholder="Type correction..."
                  className="flex-1 px-4 py-2 border rounded-lg"
                />
                <button
                  onClick={sendCorrection}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  Send
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Transcript</h2>
              <button
                onClick={() => copyToClipboard(transcript)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                📋 Copy
              </button>
            </div>
            <div className="h-64 overflow-y-auto bg-gray-50 rounded-lg p-4">
              <pre className="whitespace-pre-wrap text-sm font-mono">
                {transcript || 'Transcript will appear here...'}
              </pre>
            </div>
          </div>
        </div>

        <div className="mt-6 bg-white rounded-xl shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">
              SOAP Note - {formatTemplateName(selectedTemplate)}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={toggleEditChat}
                disabled={!soapNote}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  showEditChat 
                    ? 'bg-orange-500 text-white hover:bg-orange-600' 
                    : 'bg-green-500 text-white hover:bg-green-600'
                } ${!soapNote ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {showEditChat ? '✕ Close Chat' : '💬 Edit Chat'}
              </button>
              <button
                onClick={() => copyToClipboard(soapNote)}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                📋 Copy to EHR
              </button>
            </div>
          </div>
          
          <div className={`grid gap-4 ${showEditChat ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
            {/* SOAP Note Display */}
            <div className="bg-gray-50 rounded-lg p-4 h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm">
                {soapNote || 'SOAP note will be generated after recording...'}
              </pre>
            </div>

            {/* Edit Chat Interface */}
            {showEditChat && (
              <div className="border border-gray-200 rounded-lg flex flex-col h-96">
                <div className="bg-gray-100 px-4 py-2 rounded-t-lg flex justify-between items-center">
                  <div>
                    <h3 className="font-medium text-gray-700">AI Chat Editor</h3>
                    <p className="text-xs text-gray-500">💾 Conversations are automatically saved to AI Memory when chat is closed</p>
                  </div>
                  <button
                    onClick={clearChat}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Clear Chat
                  </button>
                </div>
                
                {/* Quick Actions - Only show when no messages yet */}
                {chatMessages.length <= 1 && (
                  <div className="px-4 py-2 bg-blue-50 border-b border-gray-200">
                    <div className="text-xs text-gray-600 mb-2">Quick actions:</div>
                    <div className="flex flex-wrap gap-2">
                      {quickActions.map((action, index) => (
                        <button
                          key={index}
                          onClick={() => sendQuickAction(action)}
                          disabled={isProcessingChat}
                          className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {chatMessages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                          message.role === 'user'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 text-gray-800'
                        }`}
                      >
                        <div className="whitespace-pre-wrap">{message.content}</div>
                        <div className={`text-xs mt-1 ${
                          message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                        }`}>
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isProcessingChat && (
                    <div className="flex justify-start">
                      <div className="bg-gray-200 text-gray-800 px-3 py-2 rounded-lg text-sm">
                        <div className="flex items-center gap-2">
                          <div className="animate-spin w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full"></div>
                          Thinking...
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Chat Input */}
                <div className="border-t border-gray-200 p-3">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendChatMessage();
                        }
                      }}
                      placeholder="Ask me to modify the SOAP note..."
                      disabled={isProcessingChat}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                    />
                    <button
                      onClick={sendChatMessage}
                      disabled={!chatInput.trim() || isProcessingChat}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      {isProcessingChat ? '...' : 'Send'}
                    </button>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Press Enter to send • Try: "Add patient allergies", "Update diagnosis", "Explain assessment"
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dentrix Integration Section */}
        {soapNote && sessionId && selectedProvider && (
          <div className="mt-6">
            <DentrixIntegration 
              sessionId={sessionId}
              soapNote={soapNote}
              providerId={selectedProvider.id}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Scribe;