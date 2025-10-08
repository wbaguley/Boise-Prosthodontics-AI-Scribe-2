import React, { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://localhost:3051';

const SessionDetail = ({ sessionId, onNavigate, onClose }) => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSOAP, setEditedSOAP] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  // Chat functionality
  const [showEditChat, setShowEditChat] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isProcessingChat, setIsProcessingChat] = useState(false);

  // Email functionality
  const [showEmailSection, setShowEmailSection] = useState(false);
  const [emailContent, setEmailContent] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [patientInfo, setPatientInfo] = useState(null);
  const [isGeneratingEmail, setIsGeneratingEmail] = useState(false);
  const [isSendingEmail, setIsSendingEmail] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  
  // Patient lookup
  const [showPatientLookup, setShowPatientLookup] = useState(false);
  const [patientSearchQuery, setPatientSearchQuery] = useState('');
  const [patientSearchResults, setPatientSearchResults] = useState([]);
  const [isSearchingPatients, setIsSearchingPatients] = useState(false);

  // Delete session
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchSessionDetails = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/sessions/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setSession(data);
        setEditedSOAP(data.soap_note || '');
      } else {
        setError('Session not found');
      }
    } catch (err) {
      setError('Failed to load session');
      console.error('Error fetching session:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSessionDetails();
  }, [fetchSessionDetails]);

  const saveChanges = async () => {
    if (!session || !editedSOAP.trim()) return;

    try {
      setIsSaving(true);
      const response = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          soap_note: editedSOAP
        })
      });

      if (response.ok) {
        setSession({ ...session, soap_note: editedSOAP });
        setIsEditing(false);
        alert('Session updated successfully!');
      } else {
        alert('Failed to save changes');
      }
    } catch (err) {
      console.error('Error saving session:', err);
      alert('Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Copied to clipboard!');
    });
  };

  // Chat functionality for SOAP note editing
  const sendChatMessage = async () => {
    if (!chatInput.trim() || isProcessingChat || !session?.soap_note) {
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
          original_soap: editedSOAP || session.soap_note,
          transcript: session.transcript || '',
          user_message: userMessage,
          chat_history: chatMessages.slice(-5)
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
        if (data.updated_soap && data.updated_soap !== (editedSOAP || session.soap_note)) {
          setEditedSOAP(data.updated_soap);
          setIsEditing(true); // Enable editing mode to show changes
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

  const toggleEditChat = () => {
    if (!session?.soap_note && !editedSOAP) {
      alert('No SOAP note to edit');
      return;
    }
    setShowEditChat(!showEditChat);
    if (!showEditChat && chatMessages.length === 0) {
      setChatMessages([{
        role: 'assistant',
        content: `Hello! I'm here to help you edit this session's SOAP note. You can ask me to:

• Add missing information
• Modify diagnoses or treatment plans  
• Change wording or terminology
• Add or remove sections
• Update patient information
• Correct any errors

What would you like to change?`,
        timestamp: new Date()
      }]);
    }
  };

  const clearChat = () => {
    setChatMessages([]);
  };

  // Email functionality functions
  const searchPatients = async () => {
    if (!patientSearchQuery.trim()) return;

    try {
      setIsSearchingPatients(true);
      const searchParams = {
        first_name: '',
        last_name: '',
        email: '',
        patient_id: ''
      };

      // Parse search query - check if it's email, ID, or name
      if (patientSearchQuery.includes('@')) {
        searchParams.email = patientSearchQuery.trim();
      } else if (/^\d+$/.test(patientSearchQuery.trim())) {
        searchParams.patient_id = patientSearchQuery.trim();
      } else {
        const nameParts = patientSearchQuery.trim().split(' ');
        searchParams.first_name = nameParts[0] || '';
        searchParams.last_name = nameParts[1] || '';
      }

      const response = await fetch(`${API_URL}/api/lookup-patient`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchParams)
      });

      if (response.ok) {
        const data = await response.json();
        setPatientSearchResults(data.patients || []);
      } else {
        console.error('Failed to search patients');
        setPatientSearchResults([]);
      }
    } catch (error) {
      console.error('Error searching patients:', error);
      setPatientSearchResults([]);
    } finally {
      setIsSearchingPatients(false);
    }
  };

  const selectPatient = async (patient) => {
    try {
      // Decrypt patient data for display
      const response = await fetch(`${API_URL}/api/decrypt-patient-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patient)
      });

      if (response.ok) {
        const decryptedPatient = await response.json();
        setPatientInfo({
          ...patient,
          email_decrypted: decryptedPatient.email,
          phone_decrypted: decryptedPatient.phone
        });
        setShowPatientLookup(false);
        setPatientSearchQuery('');
        setPatientSearchResults([]);
        
        // Auto-generate email when patient is selected
        generateEmail(decryptedPatient);
      }
    } catch (error) {
      console.error('Error selecting patient:', error);
    }
  };

  const generateEmail = async (selectedPatient = null) => {
    if (!session?.soap_note) {
      alert('No SOAP note available to generate email');
      return;
    }

    try {
      setIsGeneratingEmail(true);
      
      const patientName = selectedPatient ? 
        `${selectedPatient.first_name} ${selectedPatient.last_name}` : 
        patientInfo ? `${patientInfo.first_name} ${patientInfo.last_name}` : 'Patient';
      
      const response = await fetch(`${API_URL}/api/generate-post-visit-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          soap_note: session.soap_note,
          transcript: session.transcript,
          patient_name: patientName,
          provider_name: session.doctor || 'Dr. Smith',
          appointment_date: new Date(session.timestamp).toLocaleDateString()
        })
      });

      if (response.ok) {
        const data = await response.json();
        setEmailSubject(data.subject || 'Follow-up from your visit');
        setEmailContent(data.body || '');
        setShowEmailSection(true);
      } else {
        alert('Failed to generate email');
      }
    } catch (error) {
      console.error('Error generating email:', error);
      alert('Failed to generate email');
    } finally {
      setIsGeneratingEmail(false);
    }
  };

  const sendEmail = async () => {
    if (!patientInfo || !emailContent.trim() || !emailSubject.trim()) {
      alert('Please select a patient and ensure email content is complete');
      return;
    }

    try {
      setIsSendingEmail(true);
      
      const response = await fetch(`${API_URL}/api/send-patient-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          patient_info: patientInfo,
          email_content: emailContent,
          email_subject: emailSubject
        })
      });

      if (response.ok) {
        setEmailSent(true);
        alert('Email sent successfully!');
      } else {
        const error = await response.json();
        alert(`Failed to send email: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error sending email:', error);
      alert('Failed to send email');
    } finally {
      setIsSendingEmail(false);
    }
  };

  // Rich text formatting functions
  const formatText = (command, value = null) => {
    document.execCommand(command, false, value);
  };

  const insertList = (ordered = false) => {
    const command = ordered ? 'insertOrderedList' : 'insertUnorderedList';
    formatText(command);
  };

  // Delete session functionality
  const handleDeleteSession = async () => {
    if (deleteConfirmation !== 'DELETE') {
      alert('Please type "DELETE" to confirm');
      return;
    }

    try {
      setIsDeleting(true);
      console.log('Deleting session with ID:', sessionId);
      const response = await fetch(`${API_URL}/api/sessions/${sessionId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        console.log('Session deleted successfully');
        alert('Session deleted successfully');
        onClose(); // Close the session detail view
        // Optionally trigger a refresh of the session list
        if (onNavigate) {
          onNavigate(); // Navigate back to dashboard
        }
      } else {
        console.error('Delete response status:', response.status);
        const errorText = await response.text();
        console.error('Delete error response:', errorText);
        try {
          const error = JSON.parse(errorText);
          alert(`Failed to delete session: ${error.detail || 'Unknown error'}`);
        } catch (e) {
          alert(`Failed to delete session: ${errorText || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      alert('Failed to delete session');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
      setDeleteConfirmation('');
    }
  };

  // Quick actions
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
    setTimeout(() => {
      if (!isProcessingChat) {
        sendChatMessage();
      }
    }, 100);
  };

  const formatTemplateName = (template) => {
    if (!template) return 'Default';
    return template.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading session...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => onNavigate && onNavigate('dashboard')}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => onNavigate && onNavigate('dashboard')}
                  className="text-gray-600 hover:text-gray-800"
                >
                  ← Back
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-800">Session Details</h1>
                  <p className="text-sm text-gray-600">
                    {session?.doctor} • {new Date(session?.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsEditing(!isEditing)}
                className={`px-4 py-2 rounded-lg ${
                  isEditing ? 'bg-orange-500 hover:bg-orange-600' : 'bg-green-500 hover:bg-green-600'
                } text-white`}
              >
                {isEditing ? 'Cancel Edit' : '✏️ Edit SOAP'}
              </button>
              {isEditing && (
                <button
                  onClick={saveChanges}
                  disabled={isSaving}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              )}
              <button
                onClick={() => setShowDeleteModal(true)}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 flex items-center gap-2"
              >
                🗑️ Delete Session
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Session Info Card */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <h3 className="font-medium text-gray-700">Session ID</h3>
              <p className="text-sm text-gray-600">{session?.session_id}</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-700">Template</h3>
              <p className="text-sm text-gray-600">{formatTemplateName(session?.template_used)}</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-700">Provider</h3>
              <p className="text-sm text-gray-600">{session?.doctor}</p>
            </div>
          </div>
        </div>

        {/* Transcript Section */}
        {session?.transcript && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Original Transcript</h2>
              <button
                onClick={() => copyToClipboard(session.transcript)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                📋 Copy
              </button>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm">
                {session.transcript}
              </pre>
            </div>
          </div>
        )}

        {/* SOAP Note Section */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">
              SOAP Note - {formatTemplateName(session?.template_used)}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={toggleEditChat}
                disabled={!session?.soap_note && !editedSOAP}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  showEditChat 
                    ? 'bg-orange-500 text-white hover:bg-orange-600' 
                    : 'bg-green-500 text-white hover:bg-green-600'
                } ${(!session?.soap_note && !editedSOAP) ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {showEditChat ? '✕ Close Chat' : '💬 Edit Chat'}
              </button>
              <button
                onClick={() => copyToClipboard(editedSOAP || session?.soap_note || '')}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                📋 Copy to Dentrix
              </button>
            </div>
          </div>

          <div className={`grid gap-4 ${showEditChat ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
            {/* SOAP Note Display/Edit */}
            <div className="bg-gray-50 rounded-lg p-4 min-h-96">
              {isEditing ? (
                <div className="h-full">
                  <div className="mb-2 text-sm text-gray-600">
                    Click in the text area below to edit the SOAP note directly:
                  </div>
                  <textarea
                    value={editedSOAP}
                    onChange={(e) => setEditedSOAP(e.target.value)}
                    className="w-full h-80 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm resize-none"
                    placeholder="Enter SOAP note content..."
                  />
                </div>
              ) : (
                <div className="overflow-y-auto h-96">
                  <pre className="whitespace-pre-wrap text-sm">
                    {editedSOAP || session?.soap_note || 'No SOAP note available'}
                  </pre>
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
                
                {/* Quick Actions */}
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
                    Press Enter to send • Try: "Add patient allergies", "Update diagnosis"
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Post-Visit Email Section */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-800">Post-Visit Summary Email</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowPatientLookup(true)}
                  className="px-3 py-1 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600"
                >
                  👤 Lookup Patient
                </button>
                <button
                  onClick={() => generateEmail()}
                  disabled={isGeneratingEmail || !session?.soap_note}
                  className="px-3 py-1 bg-green-500 text-white text-sm rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isGeneratingEmail ? '⏳ Generating...' : '✨ Generate Email'}
                </button>
              </div>
            </div>

            {/* Patient Info Display */}
            {patientInfo && (
              <div className="bg-blue-50 p-3 rounded-lg mb-4">
                <div className="text-sm">
                  <span className="font-medium">Patient:</span> {patientInfo.first_name} {patientInfo.last_name}
                  <span className="ml-4 font-medium">Email:</span> {patientInfo.email_decrypted}
                  {patientInfo.phone_decrypted && (
                    <>
                      <span className="ml-4 font-medium">Phone:</span> {patientInfo.phone_decrypted}
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Email Content Editor */}
            {showEmailSection && (
              <div className="space-y-4">
                {/* Email Subject */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email Subject</label>
                  <input
                    type="text"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    placeholder="Enter email subject..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Rich Text Toolbar */}
                <div className="border border-gray-300 rounded-t-lg p-2 bg-gray-50">
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => formatText('bold')}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200"
                      title="Bold"
                    >
                      <strong>B</strong>
                    </button>
                    <button
                      onClick={() => formatText('italic')}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200"
                      title="Italic"
                    >
                      <em>I</em>
                    </button>
                    <button
                      onClick={() => formatText('underline')}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200"
                      title="Underline"
                    >
                      <u>U</u>
                    </button>
                    <div className="border-l border-gray-400 mx-1"></div>
                    <button
                      onClick={() => insertList(false)}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200"
                      title="Bullet List"
                    >
                      • List
                    </button>
                    <button
                      onClick={() => insertList(true)}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200"
                      title="Numbered List"
                    >
                      1. List
                    </button>
                    <div className="border-l border-gray-400 mx-1"></div>
                    <button
                      onClick={() => formatText('hiliteColor', 'yellow')}
                      className="px-2 py-1 border border-gray-400 rounded text-sm hover:bg-gray-200 bg-yellow-200"
                      title="Highlight"
                    >
                      HL
                    </button>
                    <select
                      onChange={(e) => formatText('fontSize', e.target.value)}
                      className="px-2 py-1 border border-gray-400 rounded text-sm"
                      defaultValue="3"
                    >
                      <option value="1">Small</option>
                      <option value="3">Normal</option>
                      <option value="5">Large</option>
                      <option value="7">Extra Large</option>
                    </select>
                  </div>
                </div>

                {/* Rich Text Editor */}
                <textarea
                  value={emailContent}
                  onChange={(e) => setEmailContent(e.target.value)}
                  className="min-h-[300px] w-full p-4 border border-gray-300 rounded-b-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-vertical"
                  style={{ borderTop: 'none' }}
                  placeholder="AI-generated email content will appear here..."
                />

                {/* Email Actions */}
                <div className="flex justify-between items-center pt-4 border-t border-gray-200">
                  <div className="text-sm text-gray-600">
                    {emailSent ? (
                      <span className="text-green-600 flex items-center gap-1">
                        ✅ Email sent successfully
                      </span>
                    ) : (
                      <span>Review and send to patient</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowEmailSection(false)}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={sendEmail}
                      disabled={isSendingEmail || !patientInfo || emailSent}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSendingEmail ? '📧 Sending...' : '📧 Send Email'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Patient Lookup Modal */}
          {showPatientLookup && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h3 className="text-lg font-semibold mb-4">Lookup Patient</h3>
                
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search by name, email, or patient ID
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={patientSearchQuery}
                      onChange={(e) => setPatientSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && searchPatients()}
                      placeholder="John Doe or john@email.com or 12345"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={searchPatients}
                      disabled={isSearchingPatients || !patientSearchQuery.trim()}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                      {isSearchingPatients ? '...' : 'Search'}
                    </button>
                  </div>
                </div>

                {/* Search Results */}
                {patientSearchResults.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Search Results:</h4>
                    <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-lg">
                      {patientSearchResults.map((patient, index) => (
                        <div
                          key={index}
                          onClick={() => selectPatient(patient)}
                          className="p-3 border-b border-gray-100 hover:bg-blue-50 cursor-pointer last:border-b-0"
                        >
                          <div className="font-medium">{patient.first_name} {patient.last_name}</div>
                          <div className="text-sm text-gray-600">ID: {patient.patient_id}</div>
                          {patient.date_of_birth && (
                            <div className="text-sm text-gray-600">DOB: {patient.date_of_birth}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => {
                      setShowPatientLookup(false);
                      setPatientSearchQuery('');
                      setPatientSearchResults([]);
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Session Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center mb-4">
                <div className="text-red-500 text-2xl mr-3">⚠️</div>
                <h3 className="text-lg font-semibold text-gray-900">Delete Session</h3>
              </div>

              <div className="mb-6">
                <p className="text-gray-600 mb-4">
                  You are about to permanently delete this session. This action cannot be undone.
                </p>
                
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                  <p className="text-red-800 font-medium">Session Details:</p>
                  <p className="text-red-700 text-sm">ID: {session?.session_id}</p>
                  <p className="text-red-700 text-sm">Date: {session?.timestamp ? new Date(session.timestamp).toLocaleDateString() : 'N/A'}</p>
                  <p className="text-red-700 text-sm">Provider: {session?.doctor || 'N/A'}</p>
                </div>

                <p className="text-gray-900 font-medium mb-2">
                  Type <span className="bg-gray-100 px-1 rounded font-mono">DELETE</span> to confirm:
                </p>
                <input
                  type="text"
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                  placeholder="Type DELETE to confirm"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  autoFocus
                />
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowDeleteModal(false);
                    setDeleteConfirmation('');
                  }}
                  disabled={isDeleting}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteSession}
                  disabled={isDeleting || deleteConfirmation !== 'DELETE'}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isDeleting ? 'Deleting...' : 'Delete Session'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionDetail;