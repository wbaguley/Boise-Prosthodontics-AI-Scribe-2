import React, { useState, useRef, useEffect } from 'react';

const API_URL = 'http://localhost:3051';
const WS_URL = 'ws://localhost:3051';

const RecordingScreen = ({ onNavigate }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [soapNote, setSoapNote] = useState('');
  const [status, setStatus] = useState('Disconnected');
  const [sessionId, setSessionId] = useState('');
  const [sessionDate, setSessionDate] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [isGeneratingSOAP, setIsGeneratingSOAP] = useState(false);
  const [correctionRequest, setCorrectionRequest] = useState('');
  const [isApplyingCorrection, setIsApplyingCorrection] = useState(false);
  
  // Chat functionality for SOAP editing
  const [showEditChat, setShowEditChat] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isProcessingChat, setIsProcessingChat] = useState(false);
  
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState('work_up');
  const [availableTemplates, setAvailableTemplates] = useState([]);
  
  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    fetchProviders();
    fetchTemplates();
    connectWebSocket();
    
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
      setAvailableTemplates(['work_up']);
    }
  };

  const connectWebSocket = () => {
    try {
      websocketRef.current = new WebSocket(`${WS_URL}/ws/audio`);
      
      websocketRef.current.onopen = () => {
        setConnectionStatus('connected');
        setStatus('Connected - Ready to record');
      };
      
      websocketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.session_id) {
            setSessionId(data.session_id);
            setSessionDate(new Date().toLocaleString());
          }
          
          if (data.status) {
            setStatus(data.status);
            
            // Update progress based on status
            if (data.status.includes('Converting audio')) {
              setProcessingStage('Converting audio');
              setProcessingProgress(25);
            } else if (data.status.includes('Transcribing')) {
              setProcessingStage('Transcribing with speaker detection');
              setProcessingProgress(50);
            } else if (data.status.includes('Generating SOAP')) {
              setProcessingStage('Generating SOAP note with AI');
              setProcessingProgress(75);
              setIsGeneratingSOAP(true);
            } else if (data.status === 'Complete') {
              setProcessingStage('Complete');
              setProcessingProgress(100);
              setIsGeneratingSOAP(false);
              setTimeout(() => {
                setProcessingProgress(0);
                setProcessingStage('');
              }, 2000);
            } else if (data.status.includes('Processing audio')) {
              setProcessingStage('Processing audio');
              setProcessingProgress(20);
            } else if (data.status.includes('chunks')) {
              // Handle recording chunk messages by showing incremental progress
              const chunkMatch = data.status.match(/(\d+) chunks/);
              if (chunkMatch) {
                const chunks = parseInt(chunkMatch[1]);
                const chunkProgress = Math.min(15 + (chunks * 2), 40); // 15% to 40% based on chunks
                setProcessingProgress(chunkProgress);
                setProcessingStage(`Recording... ${chunks} chunks`);
              }
            }
          }
          
          if (data.transcript) {
            setTranscript(data.transcript);
          }
          
          if (data.soap) {
            setSoapNote(data.soap);
            setProcessingProgress(100);
            setIsGeneratingSOAP(false);
          }
          
          if (data.error) {
            setStatus(`Error: ${data.error}`);
            setConnectionStatus('error');
            setProcessingProgress(0);
            setProcessingStage('');
            setIsGeneratingSOAP(false);
          }
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
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

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      audioChunksRef.current = [];
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : 'audio/webm';
        
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
      setTranscript('');
      setSoapNote('');
      
    } catch (error) {
      console.error('Microphone access error:', error);
      setStatus('Microphone access denied');
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setStatus('Processing audio...');
      setProcessingProgress(10);
      setProcessingStage('Preparing audio');
    }
  };

  const sendAudioToBackend = async (audioBlob) => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      setStatus('WebSocket not connected - reconnecting...');
      connectWebSocket();
      setTimeout(() => sendAudioToBackend(audioBlob), 2000);
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
      setProcessingProgress(0);
      setProcessingStage('');
    }
  };

  const applyCorrection = async () => {
    if (!correctionRequest.trim() || !soapNote) {
      alert('Please enter a correction request and ensure a SOAP note exists');
      return;
    }

    setIsApplyingCorrection(true);
    setStatus('Applying correction...');

    try {
      const response = await fetch(`${API_URL}/api/correct-soap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_soap: soapNote,
          correction: correctionRequest,
          transcript: transcript
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSoapNote(data.corrected_soap);
        setCorrectionRequest('');
        setStatus('Correction applied');
        setTimeout(() => setStatus('Connected - Ready to record'), 2000);
      } else {
        setStatus('Correction failed');
      }
    } catch (error) {
      console.error('Error applying correction:', error);
      setStatus('Correction failed');
    } finally {
      setIsApplyingCorrection(false);
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

  const toggleEditChat = () => {
    if (!soapNote) {
      setStatus('Please generate a SOAP note first before editing');
      return;
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header with Home Button */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <div className="flex items-center gap-4">
                <h1 className="text-3xl font-bold text-gray-800">
                  Recording Session
                </h1>
                <button
                  onClick={() => onNavigate && onNavigate('dashboard')}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm font-medium"
                >
                  Home
                </button>
              </div>
              <div className="text-sm text-gray-600 flex items-center gap-4 mt-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-green-500' : 
                    connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                  }`}></div>
                  <span>{status}</span>
                </div>
                {sessionId && (
                  <>
                    <span>Session: {sessionId}</span>
                    <span>{sessionDate}</span>
                  </>
                )}
              </div>
            </div>
            
            <div className="flex gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <select
                  value={selectedProvider?.id || ''}
                  onChange={(e) => {
                    const provider = providers.find(p => p.id === parseInt(e.target.value));
                    setSelectedProvider(provider);
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {providers.map(provider => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template
                </label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
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

        {/* Progress Bar */}
        {processingProgress > 0 && processingProgress < 100 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span className="font-medium">{processingStage}</span>
              <span className="font-semibold">{processingProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${processingProgress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Recording Interface */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            {/* Recording Control */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Recording Control</h2>
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={connectionStatus !== 'connected' || !selectedProvider}
                className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-all ${
                  isRecording 
                    ? 'bg-red-500 hover:bg-red-600' 
                    : 'bg-blue-500 hover:bg-blue-600'
                } ${connectionStatus !== 'connected' || !selectedProvider ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {isRecording ? 'Stop Recording' : 'Start Recording'}
              </button>
              
              {selectedProvider?.has_voice_profile && (
                <div className="mt-3 text-sm text-green-600 text-center">
                  Voice profile active for speaker identification
                </div>
              )}
              
              {connectionStatus !== 'connected' && (
                <div className="mt-3 text-sm text-red-600 text-center">
                  Not connected to backend. Check if services are running.
                </div>
              )}
            </div>

            {/* Quick Info */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="font-semibold text-gray-800 mb-3">Quick Guide</h3>
              <ul className="text-sm text-gray-600 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>Click "Start Recording" to begin</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>Speak clearly during consultation</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>System uses single-speaker mode (labels all as Doctor)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>Auto-generates SOAP note after recording</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  <span>Use correction box to request AI updates</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Transcript */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Transcript</h2>
              <button
                onClick={() => copyToClipboard(transcript)}
                disabled={!transcript}
                className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Copy
              </button>
            </div>
            <div className="h-64 overflow-y-auto bg-gray-50 rounded-lg p-4">
              {transcript ? (
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {transcript}
                </pre>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  Transcript will appear here after recording...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Correction Input */}
        {soapNote && (
          <div className="mt-6 bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold mb-3">Request Changes from AI</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={correctionRequest}
                onChange={(e) => setCorrectionRequest(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && applyCorrection()}
                placeholder="e.g., Add assessment for tooth #14, change treatment plan to include crown..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={isApplyingCorrection}
              />
              <button
                onClick={applyCorrection}
                disabled={isApplyingCorrection || !correctionRequest.trim()}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isApplyingCorrection ? 'Applying...' : 'Apply Change'}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Tell the AI what to change in the SOAP note and it will update it for you
            </p>
          </div>
        )}

        {/* SOAP Note */}
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
                disabled={!soapNote}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📋 Copy to Dentrix
              </button>
            </div>
          </div>
          
          <div className={`grid gap-4 ${showEditChat ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
            {/* SOAP Note Display */}
            <div className="bg-gray-50 rounded-lg p-4 min-h-96 overflow-y-auto">
              {isGeneratingSOAP ? (
                <div className="flex flex-col items-center justify-center h-96">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mb-4"></div>
                  <p className="text-gray-600 font-medium">Generating SOAP note with AI...</p>
                  <p className="text-gray-400 text-sm mt-2">This may take 10-30 seconds</p>
                </div>
              ) : soapNote ? (
                <pre className="whitespace-pre-wrap text-sm">
                  {soapNote}
                </pre>
              ) : (
                <div className="flex items-center justify-center h-96 text-gray-400">
                  SOAP note will be generated after recording...
                </div>
              )}
            </div>

            {/* Edit Chat Interface */}
            {showEditChat && (
              <div className="border border-gray-200 rounded-lg flex flex-col h-96">
                <div className="bg-gray-100 px-4 py-2 rounded-t-lg flex justify-between items-center">
                  <h3 className="font-medium text-gray-700">AI Chat Editor</h3>
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
      </div>
    </div>
  );
};

export default RecordingScreen;