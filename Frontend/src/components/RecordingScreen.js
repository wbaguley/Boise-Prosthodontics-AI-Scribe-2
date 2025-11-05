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

const RecordingScreen = ({ onNavigate, initialProvider }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
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
  const [selectedProvider, setSelectedProvider] = useState(initialProvider || null);
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
  const timerIntervalRef = useRef(null);

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
            } else if (data.status.includes('Transcript ready')) {
              setProcessingStage('Transcript complete');
              setProcessingProgress(100);
              // Redirect to dashboard after transcript is ready
              setTimeout(() => {
                if (onNavigate) {
                  onNavigate('dashboard');
                }
              }, 1500);
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
      setIsPaused(false);
      setRecordingTime(0);
      setStatus('Recording... Speak clearly');
      setTranscript('');
      setSoapNote('');
      
      // Start timer
      timerIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Microphone access error:', error);
      setStatus('Microphone access denied');
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      setStatus('Recording Paused');
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      setStatus('Recording... Speak clearly');
      // Resume timer
      timerIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      setStatus('Processing audio...');
      setProcessingProgress(10);
      setProcessingStage('Preparing audio');
      
      // Clear timer
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
  };

  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

  const generateSOAPNote = async () => {
    if (!transcript) {
      alert('No transcript available. Please record a session first.');
      return;
    }

    if (!sessionId) {
      alert('No session ID available. Please record a session first.');
      return;
    }

    setIsGeneratingSOAP(true);
    setStatus('Generating SOAP note with AI...');
    setProcessingStage('Generating SOAP note with AI');
    setProcessingProgress(50);

    try {
      const response = await fetch(`${API_URL}/api/sessions/${sessionId}/generate-soap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: selectedTemplate,
          doctor: selectedProvider?.name || ''
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSoapNote(data.soap_note);
        setStatus('SOAP note generated successfully');
        setProcessingProgress(100);
        setTimeout(() => {
          setProcessingProgress(0);
          setProcessingStage('');
        }, 2000);
      } else {
        const error = await response.json();
        setStatus(`Failed to generate SOAP note: ${error.detail || 'Unknown error'}`);
        setProcessingProgress(0);
        setProcessingStage('');
      }
    } catch (error) {
      console.error('Error generating SOAP note:', error);
      setStatus('Error generating SOAP note');
      setProcessingProgress(0);
      setProcessingStage('');
    } finally {
      setIsGeneratingSOAP(false);
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
                    </>
                  )}
                  {selectedProvider && (
                    <>
                      <span className="hidden sm:inline">|</span>
                      <span>Provider: {selectedProvider.name}</span>
                    </>
                  )}
                  {sessionDate && (
                    <>
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

        {/* Recording Control - Centered and Compact (Hidden when processing) */}
        {processingProgress === 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex flex-col items-center">
              {/* Timer Display */}
              {isRecording && (
                <div className="mb-3 text-2xl font-mono font-bold text-gray-700">
                  {formatTime(recordingTime)}
                </div>
              )}
              
              {/* Recording Buttons */}
              <div className="flex items-center gap-3">
              {/* Record/Stop Button */}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={connectionStatus !== 'connected' || !selectedProvider}
                className={`relative px-8 py-4 rounded-full font-bold transition-all shadow-lg border-4 ${
                  isRecording 
                    ? 'bg-gray-100 text-black border-gray-600 hover:bg-gray-200' 
                    : 'bg-gray-100 text-black border-red-500 hover:border-red-600'
                } ${connectionStatus !== 'connected' || !selectedProvider ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                title={isRecording ? 'Stop Recording' : 'Start Recording'}
              >
                {isRecording ? (
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-extrabold text-black">REC</span>
                    <div className="w-5 h-5 bg-red-500 rounded-full animate-pulse"></div>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-extrabold text-black">REC</span>
                    <div className="w-5 h-5 bg-red-500 rounded-full"></div>
                  </div>
                )}
              </button>

              {/* Pause/Resume Button - Only shown when recording */}
              {isRecording && (
                <button
                  onClick={isPaused ? resumeRecording : pauseRecording}
                  className="relative px-6 py-4 rounded-full font-bold transition-all shadow-lg border-4 border-blue-500 bg-gray-100 text-blue-600 hover:bg-gray-200 hover:scale-105"
                  title={isPaused ? 'Resume Recording' : 'Pause Recording'}
                >
                  {isPaused ? (
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                      <span className="text-sm font-bold">RESUME</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                      </svg>
                      <span className="text-sm font-bold">PAUSE</span>
                    </div>
                  )}
                </button>
              )}
            </div>
            
            {/* Status Messages */}
            <div className="mt-4 text-center space-y-1">
              {selectedProvider?.has_voice_profile && (
                <div className="text-xs text-green-600">
                  ✓ Voice profile active
                </div>
              )}
              
              {connectionStatus !== 'connected' && (
                <div className="text-xs text-red-600">
                  ⚠ Not connected to backend
                </div>
              )}
              
              {!isRecording && connectionStatus === 'connected' && selectedProvider && (
                <div className="text-xs text-gray-500">
                  Click the red button to start recording
                </div>
              )}
              
              {isRecording && !isPaused && (
                <div className="text-xs text-gray-600 animate-pulse">
                  ● Recording in progress...
                </div>
              )}
              
              {isPaused && (
                <div className="text-xs text-blue-600">
                  ⏸ Recording paused
                </div>
              )}
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default RecordingScreen;
