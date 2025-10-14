import React, { useState, useRef, useEffect } from 'react';

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
  const [selectedTemplate, setSelectedTemplate] = useState('new_patient_consultation');
  const [availableTemplates, setAvailableTemplates] = useState([]);
  
  // Post-Visit Email functionality
  const [postVisitEmail, setPostVisitEmail] = useState('');
  const [isGeneratingEmail, setIsGeneratingEmail] = useState(false);
  const [showEmailEditor, setShowEmailEditor] = useState(false);
  const [emailEditText, setEmailEditText] = useState('');
  const [savedEmails, setSavedEmails] = useState([]);
  
  const websocketRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    fetchProviders();
    fetchTemplates();
    
    // Connect to WebSocket for status checking (with connection guard)
    const timer = setTimeout(() => {
      connectWebSocket();
    }, 500); // Slight delay to avoid double connections in StrictMode
    
    return () => {
      clearTimeout(timer);
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
      setAvailableTemplates(['new_patient_consultation', 'treatment_consultation']);
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

    try {
      const wsURL = getWebSocketURL();
      console.log('Connecting to WebSocket:', wsURL);
      websocketRef.current = new WebSocket(wsURL);
      
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

      // Generate a title based on the provider and first user message
      const firstUserMessage = userMessages[0].content.substring(0, 50);
      const title = `Chat Session - ${selectedProvider || 'Unknown'} - ${firstUserMessage}...`;

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

  // Post-Visit Email Functions
  const generatePostVisitEmail = async () => {
    if (!soapNote || !selectedProvider) {
      alert('Please complete the session and select a provider first');
      return;
    }

    setIsGeneratingEmail(true);
    try {
      const response = await fetch(`${API_URL}/api/generate-post-visit-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          soap_note: soapNote,
          patient_name: 'Patient', // Could be enhanced to get actual patient name
          provider_name: selectedProvider?.name || 'Dr. Provider',
          appointment_date: sessionDate,
          transcript: transcript
        })
      });

      const result = await response.json();
      if (result.status === 'success') {
        setPostVisitEmail(result.email_content);
        setEmailEditText(result.email_content);
      } else {
        console.error('Failed to generate email:', result.message);
        alert('Failed to generate post-visit email');
      }
    } catch (error) {
      console.error('Error generating post-visit email:', error);
      alert('Error generating post-visit email');
    } finally {
      setIsGeneratingEmail(false);
    }
  };

  const savePostVisitEmail = () => {
    if (!emailEditText.trim()) return;
    
    const newEmail = {
      id: Date.now(),
      content: emailEditText,
      createdAt: new Date().toLocaleString(),
      sessionId: sessionId
    };
    
    setSavedEmails(prev => [newEmail, ...prev]);
    setPostVisitEmail(emailEditText);
    setShowEmailEditor(false);
  };

  const deleteEmail = (emailId) => {
    setSavedEmails(prev => prev.filter(email => email.id !== emailId));
  };

  const loadEmail = (email) => {
    setPostVisitEmail(email.content);
    setEmailEditText(email.content);
  };

  const copyEmailToClipboard = (content) => {
    navigator.clipboard.writeText(content);
    alert('Email copied to clipboard!');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header with Home Button */}
        <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 mb-6">
          <div className="flex flex-col gap-4">
            {/* Title and Home Button Row */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">
                  Recording Session
                </h1>
                <div className="text-sm text-gray-600 flex flex-wrap items-center gap-2 sm:gap-4 mt-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      connectionStatus === 'connected' ? 'bg-green-500' : 
                      connectionStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                    }`}></div>
                    <span>{status}</span>
                  </div>
                  {sessionId && (
                    <>
                      <span className="hidden sm:inline">|</span>
                      <span>Session: {sessionId}</span>
                      <span className="hidden sm:inline">|</span>
                      <span>{sessionDate}</span>
                    </>
                  )}
                </div>
              </div>
              
              <button
                onClick={() => onNavigate && onNavigate('dashboard')}
                className="w-full sm:w-auto px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm font-medium"
              >
                Home
              </button>
            </div>
            
            {/* Provider and Template Selection */}
            <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t border-gray-200">
              <div className="w-full sm:w-auto">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
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
                      {provider.name}
                    </option>
                  ))}
                </select>
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

        {/* Processing Indicator */}
        {processingProgress > 0 && processingProgress < 100 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex flex-col items-center justify-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mb-4"></div>
              <p className="text-gray-600 font-medium text-center">{processingStage}</p>
              <p className="text-gray-400 text-sm mt-2">Processing your recording...</p>
            </div>
          </div>
        )}

        {/* Recording Interface */}
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            {/* Recording Control */}
            <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6">
              <h2 className="text-xl font-semibold mb-4">Recording Control</h2>
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={connectionStatus !== 'connected' || !selectedProvider}
                className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-all ${
                  isRecording 
                    ? 'bg-gray-500 hover:bg-gray-600' 
                    : 'bg-red-500 hover:bg-red-600'
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
                📋 Copy to EHR
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

        {/* Post-Visit Email Section */}
        {soapNote && (
          <div className="mt-6 bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Post-Visit Summary Email</h2>
              <div className="flex gap-2">
                <button
                  onClick={generatePostVisitEmail}
                  disabled={isGeneratingEmail || !soapNote}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {isGeneratingEmail ? 'Generating...' : '✉️ Generate Email'}
                </button>
                {postVisitEmail && (
                  <button
                    onClick={() => setShowEmailEditor(!showEmailEditor)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      showEmailEditor 
                        ? 'bg-orange-500 text-white hover:bg-orange-600' 
                        : 'bg-green-500 text-white hover:bg-green-600'
                    }`}
                  >
                    {showEmailEditor ? '✕ Close Editor' : '✏️ Edit Email'}
                  </button>
                )}
              </div>
            </div>

            {/* Email Content and Editor */}
            <div className={`grid gap-4 ${showEmailEditor ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
              {/* Email Display */}
              <div className="bg-gray-50 rounded-lg p-4 min-h-64">
                {isGeneratingEmail ? (
                  <div className="flex flex-col items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mb-4"></div>
                    <p className="text-gray-600 font-medium">Generating patient-friendly email...</p>
                  </div>
                ) : postVisitEmail ? (
                  <div>
                    <div className="flex justify-between items-center mb-3">
                      <h3 className="font-medium text-gray-700">Email Preview</h3>
                      <button
                        onClick={() => copyEmailToClipboard(postVisitEmail)}
                        className="text-sm px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        📋 Copy
                      </button>
                    </div>
                    <pre className="whitespace-pre-wrap text-sm text-gray-800">
                      {postVisitEmail}
                    </pre>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-400">
                    Click "Generate Email" to create a patient-friendly summary...
                  </div>
                )}
              </div>

              {/* Email Editor */}
              {showEmailEditor && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-700 mb-3">Email Editor</h3>
                  <textarea
                    value={emailEditText}
                    onChange={(e) => setEmailEditText(e.target.value)}
                    placeholder="Edit the email content here..."
                    className="w-full h-48 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm resize-none"
                  />
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={savePostVisitEmail}
                      disabled={!emailEditText.trim()}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 text-sm"
                    >
                      💾 Save Email
                    </button>
                    <button
                      onClick={generatePostVisitEmail}
                      disabled={isGeneratingEmail}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 text-sm"
                    >
                      🔄 Regenerate
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Saved Emails List */}
            {savedEmails.length > 0 && (
              <div className="mt-6 border-t pt-4">
                <h3 className="font-medium text-gray-700 mb-3">Saved Emails ({savedEmails.length})</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {savedEmails.map((email) => (
                    <div key={email.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          Email saved on {email.createdAt}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {email.content.substring(0, 100)}...
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => loadEmail(email)}
                          className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                        >
                          Load
                        </button>
                        <button
                          onClick={() => copyEmailToClipboard(email.content)}
                          className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
                        >
                          Copy
                        </button>
                        <button
                          onClick={() => deleteEmail(email.id)}
                          className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecordingScreen;