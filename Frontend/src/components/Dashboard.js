import React, { useState, useEffect, useRef } from 'react';
import VoiceProfile from './Voiceprofile';

const API_URL = process.env.REACT_APP_API_URL || '';

const Dashboard = ({ onNavigate }) => {
  const [sessions, setSessions] = useState([]);
  const [providers, setProviders] = useState([]);
  const [systemStatus, setSystemStatus] = useState({
    whisper: 'checking',
    ollama: 'checking',
    voice_profiles: 'checking'
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Settings state
  const [newProviderName, setNewProviderName] = useState('');
  const [newProviderSpecialty, setNewProviderSpecialty] = useState('');
  const [newProviderCredentials, setNewProviderCredentials] = useState('');
  const [showVoiceTraining, setShowVoiceTraining] = useState(false);
  const [selectedTrainingProvider, setSelectedTrainingProvider] = useState(null);
  
  // Template management state
  const [templates, setTemplates] = useState([]);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [newTemplate, setNewTemplate] = useState({
    id: '',
    name: '',
    description: '',
    ai_instructions: '',
    sections: {
      SUBJECTIVE: [],
      OBJECTIVE: [],
      ASSESSMENT: [],
      PLAN: []
    }
  });

  // Configuration management state
  const [showConfigManager, setShowConfigManager] = useState(false);
  const [configData, setConfigData] = useState({
    email: {
      smtp_server: '',
      smtp_port: 587,
      smtp_username: '',
      smtp_password: '',
      configured: false
    },
    dentrix: {
      api_url: '',
      api_key: '',
      configured: false
    }
  });
  const [configLoading, setConfigLoading] = useState(false);
  const [configActiveTab, setConfigActiveTab] = useState('email');

  // AI Training state
  const [knowledgeArticles, setKnowledgeArticles] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isTrainingChat, setIsTrainingChat] = useState(false);
  const [newArticle, setNewArticle] = useState({ title: '', content: '', category: '' });
  const [showArticleEditor, setShowArticleEditor] = useState(false);

  // Delete session state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  // Reorganized settings state
  const [settingsActiveSection, setSettingsActiveSection] = useState('providers'); // providers, templates, system, users
  const [showProviderSettings, setShowProviderSettings] = useState(false);
  const [showTemplateSettings, setShowTemplateSettings] = useState(false);
  const [showSystemSettings, setShowSystemSettings] = useState(false);
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [showAITraining, setShowAITraining] = useState(false);

  // User Management state
  const [users, setUsers] = useState([]);
  const [showUserModal, setShowUserModal] = useState(false);
  const [newUser, setNewUser] = useState({ name: '', email: '', role: 'user' });
  const [isInvitingUser, setIsInvitingUser] = useState(false);

  // AI Memory state
  const [aiMemories, setAiMemories] = useState([
    { id: 1, title: 'Crown procedures', addedDate: '2 days ago' },
    { id: 2, title: 'Implant protocols', addedDate: '1 week ago' },
    { id: 3, title: 'Patient consultation guidelines', addedDate: '2 weeks ago' },
    { id: 4, title: 'SOAP note formatting', addedDate: '3 weeks ago' }
  ]);
  const [showMemoryEditor, setShowMemoryEditor] = useState(false);
  const [showAllMemories, setShowAllMemories] = useState(false);
  const [editingMemory, setEditingMemory] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  // File upload reference
  const fileInputRef = useRef(null);

  // Handlers for AI Training features
  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    files.forEach(file => {
      console.log('Uploading file:', file.name);
      // Here you would typically upload to your backend
      // For now, we'll just add to the uploaded files list
      setUploadedFiles(prev => [...prev, {
        id: Date.now() + Math.random(),
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date().toLocaleDateString()
      }]);
    });
    // Reset the input
    event.target.value = '';
  };

  const handleBrowseFiles = () => {
    fileInputRef.current?.click();
  };

  const handleViewAllMemories = () => {
    setShowAllMemories(true);
  };

  const deleteMemory = (memoryId) => {
    setAiMemories(prev => prev.filter(memory => memory.id !== memoryId));
  };

  useEffect(() => {
    fetchSystemStatus();
    fetchSessions();
    fetchProviders();
    fetchTemplates();
    fetchConfiguration();
    fetchKnowledgeArticles();
    
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      const data = await response.json();
      setSystemStatus({
        whisper: data.whisper || 'unknown',
        ollama: data.ollama || 'unknown',
        voice_profiles: data.voice_profiles || 'unknown'
      });
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_URL}/api/sessions`);
      const data = await response.json();
      setSessions(data.slice(0, 10));
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/providers`);
      const data = await response.json();
      setProviders(data);
    } catch (error) {
      console.error('Error fetching providers:', error);
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
        setNewProviderName('');
        setNewProviderSpecialty('');
        setNewProviderCredentials('');
        fetchProviders();
        alert('Provider added successfully');
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
        fetchProviders();
        alert('Provider deleted successfully');
      } else {
        alert('Failed to delete provider');
      }
    } catch (error) {
      console.error('Error deleting provider:', error);
      alert('Failed to delete provider');
    }
  };

  const handleVoiceProfileSaved = () => {
    fetchProviders();
    setShowVoiceTraining(false);
    setSelectedTrainingProvider(null);
  };

  // Template Management Functions
  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_URL}/api/templates/list`);
      const data = await response.json();
      setTemplates(data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const createTemplate = async () => {
    if (!newTemplate.name.trim() || !newTemplate.id.trim()) {
      alert('Template name and ID are required');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTemplate)
      });

      if (response.ok) {
        fetchTemplates();
        resetTemplateForm();
        setShowTemplateEditor(false);
        alert('Template created successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create template');
      }
    } catch (error) {
      console.error('Error creating template:', error);
      alert('Failed to create template');
    }
  };

  const updateTemplate = async () => {
    if (!editingTemplate || !newTemplate.name.trim()) {
      alert('Template name is required');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/templates/${editingTemplate.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTemplate)
      });

      if (response.ok) {
        fetchTemplates();
        resetTemplateForm();
        setShowTemplateEditor(false);
        setEditingTemplate(null);
        alert('Template updated successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to update template');
      }
    } catch (error) {
      console.error('Error updating template:', error);
      alert('Failed to update template');
    }
  };

  const deleteTemplate = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/templates/${templateId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        fetchTemplates();
        alert('Template deleted successfully');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to delete template');
      }
    } catch (error) {
      console.error('Error deleting template:', error);
      alert('Failed to delete template');
    }
  };

  const editTemplate = async (templateId) => {
    try {
      const response = await fetch(`${API_URL}/api/templates/${templateId}`);
      if (response.ok) {
        const template = await response.json();
        setNewTemplate({
          id: templateId,
          name: template.name || '',
          description: template.description || '',
          ai_instructions: template.ai_instructions || '',
          sections: template.sections || {
            SUBJECTIVE: [],
            OBJECTIVE: [],
            ASSESSMENT: [],
            PLAN: []
          }
        });
        setEditingTemplate({ id: templateId, name: template.name });
        setShowTemplateEditor(true);
      }
    } catch (error) {
      console.error('Error loading template:', error);
      alert('Failed to load template');
    }
  };

  const resetTemplateForm = () => {
    setNewTemplate({
      id: '',
      name: '',
      description: '',
      ai_instructions: '',
      sections: {
        SUBJECTIVE: [],
        OBJECTIVE: [],
        ASSESSMENT: [],
        PLAN: []
      }
    });
    setEditingTemplate(null);
  };

  const addSectionItem = (sectionName) => {
    const newItem = prompt(`Add new ${sectionName} item:`);
    if (newItem && newItem.trim()) {
      setNewTemplate(prev => ({
        ...prev,
        sections: {
          ...prev.sections,
          [sectionName]: [...prev.sections[sectionName], newItem.trim()]
        }
      }));
    }
  };

  const removeSectionItem = (sectionName, index) => {
    setNewTemplate(prev => ({
      ...prev,
      sections: {
        ...prev.sections,
        [sectionName]: prev.sections[sectionName].filter((_, i) => i !== index)
      }
    }));
  };

  const getStatusColor = (status) => {
    if (status === 'enabled' || status === 'healthy') return 'bg-green-500';
    if (status === 'disabled' || status === 'unreachable') return 'bg-red-500';
    return 'bg-yellow-500';
  };

  const getStatusText = (status) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  // Configuration management functions
  const fetchConfiguration = async () => {
    try {
      const response = await fetch(`${API_URL}/api/config`);
      if (response.ok) {
        const config = await response.json();
        setConfigData(config);
      }
    } catch (error) {
      console.error('Failed to fetch configuration:', error);
    }
  };

  const updateEmailConfig = async (emailConfig) => {
    try {
      setConfigLoading(true);
      const response = await fetch(`${API_URL}/api/config/email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(emailConfig)
      });
      
      if (response.ok) {
        await fetchConfiguration(); // Refresh config
        alert('Email configuration updated successfully!');
      } else {
        throw new Error('Failed to update email configuration');
      }
    } catch (error) {
      console.error('Email config error:', error);
      alert('Failed to update email configuration');
    } finally {
      setConfigLoading(false);
    }
  };

  const updateDentrixConfig = async (dentrixConfig) => {
    try {
      setConfigLoading(true);
      const response = await fetch(`${API_URL}/api/config/dentrix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dentrixConfig)
      });
      
      if (response.ok) {
        await fetchConfiguration(); // Refresh config
        alert('Dentrix configuration updated successfully!');
      } else {
        throw new Error('Failed to update Dentrix configuration');
      }
    } catch (error) {
      console.error('Dentrix config error:', error);
      alert('Failed to update Dentrix configuration');
    } finally {
      setConfigLoading(false);
    }
  };

  const testEmailConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/config/test-email`, {
        method: 'POST'
      });
      
      if (response.ok) {
        alert('Test email sent successfully! Check your inbox.');
      } else {
        const error = await response.json();
        alert(`Test failed: ${error.detail}`);
      }
    } catch (error) {
      console.error('Email test error:', error);
      alert('Failed to send test email');
    }
  };

  const testDentrixConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/config/test-dentrix`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Dentrix test: ${result.message}`);
      } else {
        alert('Dentrix connection test failed');
      }
    } catch (error) {
      console.error('Dentrix test error:', error);
      alert('Failed to test Dentrix connection');
    }
  };

  // AI Training Functions
  const fetchKnowledgeArticles = async () => {
    try {
      const response = await fetch(`${API_URL}/api/knowledge-articles`);
      if (response.ok) {
        const articles = await response.json();
        setKnowledgeArticles(articles);
      }
    } catch (error) {
      console.error('Error fetching knowledge articles:', error);
    }
  };

  const createKnowledgeArticle = async (e) => {
    e.preventDefault();
    if (!newArticle.title || !newArticle.content || !newArticle.category) {
      alert('Please fill in all fields');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/knowledge-articles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newArticle)
      });

      if (response.ok) {
        await fetchKnowledgeArticles();
        setNewArticle({ title: '', content: '', category: '' });
        setShowArticleEditor(false);
        alert('Knowledge article created successfully!');
      } else {
        alert('Failed to create knowledge article');
      }
    } catch (error) {
      console.error('Error creating knowledge article:', error);
      alert('Failed to create knowledge article');
    }
  };

  const deleteKnowledgeArticle = async (articleId) => {
    if (!window.confirm('Are you sure you want to delete this article?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/knowledge-articles/${articleId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchKnowledgeArticles();
        alert('Article deleted successfully');
      } else {
        alert('Failed to delete article');
      }
    } catch (error) {
      console.error('Error deleting article:', error);
      alert('Failed to delete article');
    }
  };

  const sendTrainingMessage = async () => {
    if (!chatInput.trim() || isTrainingChat) return;

    const userMessage = {
      role: 'user',
      content: chatInput,
      timestamp: new Date().toISOString()
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsTrainingChat(true);

    try {
      const response = await fetch(`${API_URL}/api/ai-training/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: chatInput })
      });

      if (response.ok) {
        const result = await response.json();
        const aiMessage = {
          role: 'assistant',
          content: result.response,
          timestamp: new Date().toISOString()
        };
        setChatMessages(prev => [...prev, aiMessage]);
      } else {
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your message.',
          timestamp: new Date().toISOString()
        };
        setChatMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Training chat error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your message.',
        timestamp: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTrainingChat(false);
    }
  };

  // Delete session functionality
  const handleDeleteSession = async () => {
    if (!sessionToDelete || deleteConfirmation !== 'DELETE') {
      alert('Please type "DELETE" to confirm');
      return;
    }

    try {
      setIsDeleting(true);
      const response = await fetch(`${API_URL}/api/sessions/${sessionToDelete.session_id}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        alert('Session deleted successfully');
        await fetchSessions(); // Refresh the sessions list
      } else {
        const error = await response.json();
        alert(`Failed to delete session: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      alert('Failed to delete session');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
      setSessionToDelete(null);
      setDeleteConfirmation('');
    }
  };

  const openDeleteModal = (session, event) => {
    event.stopPropagation(); // Prevent navigation when clicking delete
    setSessionToDelete(session);
    setShowDeleteModal(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Boise Prosthodontics AI Scribe</h1>
              <p className="text-sm text-gray-600 mt-1">Dashboard</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
              <button
                onClick={() => setShowAITraining(true)}
                className="w-full sm:w-auto px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center justify-center gap-2 text-sm"
              >
                🤖 AI Training
              </button>
              <button
                onClick={() => setShowSettings(true)}
                className="w-full sm:w-auto px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 flex items-center justify-center gap-2 text-sm"
              >
                Settings
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Quick Actions - Mobile First */}
        <div className="mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8">
            <h2 className="text-xl font-semibold mb-6 text-gray-800">Quick Actions</h2>
            
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
              <button
                onClick={() => onNavigate && onNavigate('recording')}
                className="flex-1 py-4 sm:py-6 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-base sm:text-lg font-semibold transition-all transform hover:scale-105"
              >
                Start New Session
              </button>

              <button
                onClick={() => onNavigate && onNavigate('session-history')}
                className="flex-1 py-3 sm:py-4 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-semibold transition-all"
              >
                📋 View All Sessions
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <span>Real-time transcription</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span>Speaker identification</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                <span>Auto SOAP generation</span>
              </div>
            </div>
          </div>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs sm:text-sm font-medium text-gray-600">Whisper Status</h3>
              <div className={`w-3 h-3 rounded-full ${getStatusColor(systemStatus.whisper)}`}></div>
            </div>
            <p className="text-lg sm:text-2xl font-bold text-gray-800">{getStatusText(systemStatus.whisper)}</p>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs sm:text-sm font-medium text-gray-600">Ollama (AI)</h3>
              <div className={`w-3 h-3 rounded-full ${getStatusColor(systemStatus.ollama)}`}></div>
            </div>
            <p className="text-lg sm:text-2xl font-bold text-gray-800">{getStatusText(systemStatus.ollama)}</p>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs sm:text-sm font-medium text-gray-600">Voice Profiles</h3>
              <div className={`w-3 h-3 rounded-full ${getStatusColor(systemStatus.voice_profiles)}`}></div>
            </div>
            <p className="text-lg sm:text-2xl font-bold text-gray-800">{providers.filter(p => p.has_voice_profile).length}/{providers.length}</p>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs sm:text-sm font-medium text-gray-600">Total Sessions</h3>
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            </div>
            <p className="text-lg sm:text-2xl font-bold text-gray-800">{sessions.length}</p>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-1 gap-8">
          {/* Recent Sessions - Full Width */}
          <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-800">Recent Sessions</h2>
                <button
                  onClick={() => onNavigate && onNavigate('session-history')}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View All →
                </button>
              </div>
              
              {sessions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No sessions yet</p>
                  <p className="text-sm mt-2">Start your first recording session above</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {sessions.map((session) => (
                    <div
                      key={session.session_id}
                      onClick={() => onNavigate && onNavigate('session-detail', session.session_id)}
                      className="p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 cursor-pointer transition-all"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-medium text-gray-800">{session.doctor}</div>
                          <div className="text-sm text-gray-600">
                            {new Date(session.timestamp).toLocaleString()}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            ID: {session.session_id}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <div className="text-xs text-gray-500">
                            {session.template_used ? 
                              session.template_used.split('_').map(word => 
                                word.charAt(0).toUpperCase() + word.slice(1)
                              ).join(' ') : 'Default'
                            }
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={(e) => openDeleteModal(session, e)}
                              className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors"
                              title="Delete Session"
                            >
                              🗑️
                            </button>
                            <div className="text-xs text-blue-600 font-medium">
                              Click to view/edit →
                            </div>
                          </div>
                        </div>
                      </div>
                      {session.transcript && (
                        <div className="text-sm text-gray-600 mt-2 line-clamp-2">
                          {session.transcript.substring(0, 150)}
                          {session.transcript.length > 150 && '...'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
        </div>
      </div>

      {/* Main Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">System Settings</h3>
                <button
                  onClick={() => setShowSettings(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                
                {/* Providers & Voice Training */}
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-6 cursor-pointer hover:shadow-lg transition-all"
                     onClick={() => setShowProviderSettings(true)}>
                  <div className="text-center">
                    <div className="text-4xl mb-4">👥</div>
                    <h4 className="font-semibold text-lg text-gray-800">Providers & Voice Training</h4>
                    <p className="text-sm text-gray-600 mt-2">Add providers and train voice profiles</p>
                    <div className="mt-4 text-xs text-blue-600">
                      {providers.length} Provider{providers.length !== 1 ? 's' : ''} Added
                    </div>
                  </div>
                </div>

                {/* SOAP Templates */}
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-6 cursor-pointer hover:shadow-lg transition-all"
                     onClick={() => setShowTemplateSettings(true)}>
                  <div className="text-center">
                    <div className="text-4xl mb-4">📋</div>
                    <h4 className="font-semibold text-lg text-gray-800">SOAP Templates</h4>
                    <p className="text-sm text-gray-600 mt-2">Create and manage SOAP templates</p>
                    <div className="mt-4 text-xs text-green-600">
                      {templates.length} Template{templates.length !== 1 ? 's' : ''} Created
                    </div>
                  </div>
                </div>

                {/* System Configuration */}
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-6 cursor-pointer hover:shadow-lg transition-all"
                     onClick={() => setShowSystemSettings(true)}>
                  <div className="text-center">
                    <div className="text-4xl mb-4">⚙️</div>
                    <h4 className="font-semibold text-lg text-gray-800">System Configuration</h4>
                    <p className="text-sm text-gray-600 mt-2">Email, Dentrix API, AI Training</p>
                    <div className="mt-4 text-xs text-purple-600">
                      {(configData.email.configured ? 1 : 0) + (configData.dentrix.configured ? 1 : 0)}/2 Configured
                    </div>
                  </div>
                </div>

                {/* User Management */}
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl p-6 cursor-pointer hover:shadow-lg transition-all"
                     onClick={() => setShowUserManagement(true)}>
                  <div className="text-center">
                    <div className="text-4xl mb-4">👤</div>
                    <h4 className="font-semibold text-lg text-gray-800">User Management</h4>
                    <p className="text-sm text-gray-600 mt-2">Add and manage users</p>
                    <div className="mt-4 text-xs text-orange-600">
                      {users.length} User{users.length !== 1 ? 's' : ''} Registered
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      )}

      {/* Provider Settings Modal */}
      {showProviderSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">Providers & Voice Training</h3>
                <button
                  onClick={() => setShowProviderSettings(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Add New Provider */}
              <div className="bg-blue-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Add New Provider</h4>
                <div className="space-y-3">
                  <input
                    type="text"
                    value={newProviderName}
                    onChange={(e) => setNewProviderName(e.target.value)}
                    placeholder="Provider Name (e.g., Dr. Smith)"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <input
                    type="text"
                    value={newProviderSpecialty}
                    onChange={(e) => setNewProviderSpecialty(e.target.value)}
                    placeholder="Specialty (optional)"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <input
                    type="text"
                    value={newProviderCredentials}
                    onChange={(e) => setNewProviderCredentials(e.target.value)}
                    placeholder="Credentials (optional, e.g., DDS, MS)"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={createProvider}
                    className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Add Provider
                  </button>
                </div>
              </div>

              {/* Existing Providers */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Providers</h4>
                {providers.length === 0 ? (
                  <p className="text-gray-500 text-sm">No providers added yet</p>
                ) : (
                  <div className="space-y-3">
                    {providers.map((provider) => (
                      <div key={provider.id} className="flex justify-between items-center p-3 bg-white rounded-lg border">
                        <div>
                          <div className="font-medium">{provider.name}</div>
                          {(provider.specialty || provider.credentials) && (
                            <div className="text-sm text-gray-600">
                              {[provider.specialty, provider.credentials].filter(Boolean).join(' • ')}
                            </div>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setSelectedTrainingProvider(provider);
                              setShowVoiceTraining(true);
                            }}
                            className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-sm"
                          >
                            🎤 Train Voice
                          </button>
                          <button
                            onClick={() => deleteProvider(provider.id)}
                            className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Template Settings Modal */}
      {showTemplateSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">SOAP Templates</h3>
                <button
                  onClick={() => setShowTemplateSettings(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h4 className="text-lg font-semibold">Manage Templates</h4>
                  <p className="text-gray-600">Create and customize SOAP note templates</p>
                </div>
                <button
                  onClick={() => setShowTemplateEditor(true)}
                  className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  + Add Template
                </button>
              </div>
              
              {templates.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-4xl mb-4">📋</div>
                  <p>No custom templates created yet</p>
                  <p className="text-sm mt-2">Create your first template above</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {templates.map((template) => (
                    <div key={template.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h5 className="font-medium text-lg">{template.name}</h5>
                          <p className="text-gray-600 text-sm mt-1">{template.description}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setEditingTemplate(template);
                              setNewTemplate({
                                name: template.name,
                                description: template.description,
                                content: template.content
                              });
                              setShowTemplateEditor(true);
                            }}
                            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => deleteTemplate(template.id)}
                            className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* System Configuration Modal */}
      {showSystemSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">System Configuration</h3>
                <button
                  onClick={() => setShowSystemSettings(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* AI/Ollama Configuration */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">AI Model Configuration (Ollama)</h4>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Ollama Host URL
                    </label>
                    <input
                      type="text"
                      defaultValue={configData.ai?.ollama_host || 'http://ollama:11434'}
                      id="ollama-host-input"
                      placeholder="http://localhost:11434"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default: http://ollama:11434 (Docker) or http://localhost:11434 (Local)
                    </p>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        const input = document.getElementById('ollama-host-input');
                        const ollamaHost = input.value;
                        
                        try {
                          const response = await fetch(`${API_URL}/api/config/ai`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ollama_host: ollamaHost })
                          });
                          
                          const result = await response.json();
                          if (result.status === 'success') {
                            alert('Ollama configuration updated! Please refresh the page.');
                            await fetchConfiguration();
                          } else {
                            alert(`Failed: ${result.message}`);
                          }
                        } catch (error) {
                          alert('Failed to update Ollama configuration');
                        }
                      }}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                    >
                      Save Ollama Config
                    </button>
                    
                    <button
                      onClick={async () => {
                        try {
                          const response = await fetch(`${API_URL}/api/config/test-ollama`, {
                            method: 'POST'
                          });
                          
                          const result = await response.json();
                          if (result.status === 'success') {
                            alert(`✅ Connected to Ollama!\n\nHost: ${result.host}\nModels: ${result.models.map(m => m.name).join(', ')}`);
                          } else {
                            alert(`❌ Connection failed:\n${result.message}\n\nHost: ${result.host}`);
                          }
                        } catch (error) {
                          alert('Failed to test Ollama connection');
                        }
                      }}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                    >
                      Test Connection
                    </button>
                  </div>
                  
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
                    <p className="font-medium text-yellow-800 mb-1">🔧 Troubleshooting:</p>
                    <ul className="text-yellow-700 space-y-1 list-disc list-inside">
                      <li>If using Docker: Use <code className="bg-yellow-100 px-1">http://ollama:11434</code></li>
                      <li>If running locally: Use <code className="bg-yellow-100 px-1">http://localhost:11434</code></li>
                      <li>Make sure Ollama service is running: <code className="bg-yellow-100 px-1">docker-compose ps</code></li>
                      <li>Check Ollama logs: <code className="bg-yellow-100 px-1">docker-compose logs ollama</code></li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Email Setup */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Email Configuration</h4>
                <div className="grid md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="SMTP Server"
                    defaultValue={configData.email?.smtp_server}
                    id="smtp-server"
                    className="px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="number"
                    placeholder="Port"
                    defaultValue={configData.email?.smtp_port || 587}
                    id="smtp-port"
                    className="px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="email"
                    placeholder="Email Address"
                    defaultValue={configData.email?.smtp_username}
                    id="smtp-username"
                    className="px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="password"
                    placeholder="Password"
                    id="smtp-password"
                    className="px-3 py-2 border rounded-lg"
                  />
                </div>
                <button 
                  onClick={async () => {
                    const emailConfig = {
                      smtp_server: document.getElementById('smtp-server').value,
                      smtp_port: parseInt(document.getElementById('smtp-port').value),
                      smtp_username: document.getElementById('smtp-username').value,
                      smtp_password: document.getElementById('smtp-password').value
                    };
                    await updateEmailConfig(emailConfig);
                  }}
                  className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  Save Email Settings
                </button>
              </div>

              {/* Dentrix API */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Dentrix API Connection</h4>
                <div className="grid md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="API Endpoint"
                    defaultValue={configData.dentrix?.api_url}
                    id="dentrix-url"
                    className="px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="text"
                    placeholder="API Key"
                    id="dentrix-key"
                    className="px-3 py-2 border rounded-lg"
                  />
                </div>
                <button 
                  onClick={async () => {
                    const dentrixConfig = {
                      api_url: document.getElementById('dentrix-url').value,
                      api_key: document.getElementById('dentrix-key').value
                    };
                    await updateDentrixConfig(dentrixConfig);
                  }}
                  className="mt-4 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                >
                  Test Connection
                </button>
              </div>


            </div>
          </div>
        </div>
      )}

      {/* User Management Modal */}
      {showUserManagement && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">User Management</h3>
                <button
                  onClick={() => setShowUserManagement(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Add New User */}
              <div className="bg-green-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Invite New User</h4>
                <div className="space-y-3">
                  <input
                    type="email"
                    placeholder="Email Address"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500">
                    <option value="">Select Role</option>
                    <option value="admin">Administrator</option>
                    <option value="provider">Provider</option>
                    <option value="staff">Staff</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  <button className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
                    Send Invitation
                  </button>
                </div>
              </div>

              {/* Current Users */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h4 className="font-semibold text-lg mb-4">Current Users</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-white rounded-lg border">
                    <div>
                      <div className="font-medium">admin@boiseprosthodontics.com</div>
                      <div className="text-sm text-gray-600">Administrator • Last active: Today</div>
                    </div>
                    <div className="flex gap-2">
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">Admin</span>
                      <button className="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm">
                        Edit
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Training Modal */}
      {showAITraining && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-[95vw] max-h-[95vh] overflow-hidden">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">AI Model Training</h3>
                <button
                  onClick={() => setShowAITraining(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="flex h-[80vh]">
              {/* Left Panel - Chat Interface */}
              <div className="flex-1 flex flex-col border-r">
                <div className="p-4 bg-gray-50 border-b">
                  <h4 className="font-semibold">Chat with AI Model</h4>
                  <p className="text-sm text-gray-600">Train and interact with the AI to improve its responses</p>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="font-medium text-sm text-blue-800">AI Model</div>
                    <div className="mt-1">Hello! I'm ready to learn. You can ask me questions about prosthodontics or provide training examples.</div>
                  </div>
                </div>
                
                <div className="p-4 border-t">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Type your message to train the AI..."
                      className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                    />
                    <button className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600">
                      Send
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Panel - Knowledge Management */}
              <div className="w-80 flex flex-col">
                <div className="p-4 bg-gray-50 border-b">
                  <h4 className="font-semibold">Knowledge Base</h4>
                  <p className="text-sm text-gray-600">Upload documents and manage AI memory</p>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4">
                  {/* Upload Section */}
                  <div className="mb-6">
                    <h5 className="font-medium mb-2">Upload Documents</h5>
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-purple-400 transition-colors">
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".pdf,.doc,.docx,.txt,.md"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      <div className="text-gray-500 text-sm">
                        <div className="text-2xl mb-2">📄</div>
                        Drag & drop files here or
                        <button 
                          className="text-purple-500 underline ml-1 hover:text-purple-700"
                          onClick={handleBrowseFiles}
                        >
                          click to browse
                        </button>
                      </div>
                    </div>
                    
                    {/* Show uploaded files */}
                    {uploadedFiles.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {uploadedFiles.map(file => (
                          <div key={file.id} className="flex items-center justify-between p-2 bg-purple-50 rounded text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-purple-600">📄</span>
                              <span className="font-medium">{file.name}</span>
                              <span className="text-gray-500">({(file.size / 1024).toFixed(1)} KB)</span>
                            </div>
                            <span className="text-xs text-gray-500">{file.uploadDate}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Memory Management */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h5 className="font-medium">AI Memory</h5>
                      <button 
                        className="text-sm text-purple-500 hover:text-purple-700"
                        onClick={handleViewAllMemories}
                      >
                        View All
                      </button>
                    </div>
                    <div className="space-y-2">
                      {aiMemories.slice(0, 2).map(memory => (
                        <div key={memory.id} className="p-2 bg-gray-50 rounded text-sm">
                          <div className="font-medium">{memory.title}</div>
                          <div className="text-gray-600 text-xs">Added {memory.addedDate}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Voice Training Modal */}
      {showVoiceTraining && selectedTrainingProvider && (
        <VoiceProfile
          doctorName={selectedTrainingProvider.name}
          onClose={() => {
            setShowVoiceTraining(false);
            setSelectedTrainingProvider(null);
          }}
          onSave={handleVoiceProfileSaved}
        />
      )}

      {/* Template Editor Modal */}
      {showTemplateEditor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">
                  {editingTemplate ? 'Edit Template' : 'Create New Template'}
                </h3>
                <button
                  onClick={() => {
                    setShowTemplateEditor(false);
                    resetTemplateForm();
                  }}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Basic Template Info */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Template ID (used internally)
                  </label>
                  <input
                    type="text"
                    value={newTemplate.id}
                    onChange={(e) => setNewTemplate(prev => ({ ...prev, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') }))}
                    placeholder="e.g., custom_template"
                    disabled={!!editingTemplate}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Template Name
                  </label>
                  <input
                    type="text"
                    value={newTemplate.name}
                    onChange={(e) => setNewTemplate(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Emergency Visit"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={newTemplate.description}
                  onChange={(e) => setNewTemplate(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of when to use this template"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  AI Instructions
                </label>
                <textarea
                  value={newTemplate.ai_instructions}
                  onChange={(e) => setNewTemplate(prev => ({ ...prev, ai_instructions: e.target.value }))}
                  placeholder="Instructions for the AI on how to use this template. E.g., 'Focus on emergency procedures and pain management. Document urgency level and immediate interventions.'"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <div className="text-xs text-gray-500 mt-1">
                  These instructions help the AI generate more accurate SOAP notes for this specific type of visit.
                </div>
              </div>

              {/* SOAP Sections */}
              <div>
                <h4 className="text-lg font-semibold mb-4">SOAP Template Structure</h4>
                <div className="grid md:grid-cols-2 gap-6">
                  {Object.entries(newTemplate.sections).map(([sectionName, items]) => (
                    <div key={sectionName} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-3">
                        <h5 className="font-medium text-gray-800">{sectionName}</h5>
                        <button
                          onClick={() => addSectionItem(sectionName)}
                          className="text-sm bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                        >
                          + Add Item
                        </button>
                      </div>
                      <div className="space-y-2">
                        {items.map((item, index) => (
                          <div key={index} className="flex items-center justify-between bg-white p-2 rounded">
                            <span className="text-sm">{item}</span>
                            <button
                              onClick={() => removeSectionItem(sectionName, index)}
                              className="text-red-500 hover:text-red-700 text-sm"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                        {items.length === 0 && (
                          <div className="text-gray-500 text-sm italic">
                            No items yet. Click "Add Item" to add elements for this section.
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => {
                    setShowTemplateEditor(false);
                    resetTemplateForm();
                  }}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                >
                  Cancel
                </button>
                <button
                  onClick={editingTemplate ? updateTemplate : createTemplate}
                  disabled={!newTemplate.name.trim() || !newTemplate.id.trim()}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {editingTemplate ? 'Update Template' : 'Create Template'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Configuration Management Modal */}
      {showConfigManager && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">System Configuration</h3>
                <button
                  onClick={() => setShowConfigManager(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              {/* Configuration Tabs */}
              <div className="flex mb-6 border-b border-gray-200">
                <button
                  onClick={() => setConfigActiveTab('email')}
                  className={`px-4 py-2 font-medium ${
                    configActiveTab === 'email'
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-600 hover:text-blue-600'
                  }`}
                >
                  📧 Email Configuration
                </button>
                <button
                  onClick={() => setConfigActiveTab('dentrix')}
                  className={`px-4 py-2 font-medium ${
                    configActiveTab === 'dentrix'
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-600 hover:text-blue-600'
                  }`}
                >
                  🦷 Dentrix API
                </button>
                <button
                  onClick={() => setConfigActiveTab('ai-training')}
                  className={`px-4 py-2 font-medium ${
                    configActiveTab === 'ai-training'
                      ? 'border-b-2 border-blue-500 text-blue-600'
                      : 'text-gray-600 hover:text-blue-600'
                  }`}
                >
                  🧠 AI Training
                </button>
              </div>

              {/* Email Configuration Tab */}
              {configActiveTab === 'email' && (
                <div className="space-y-6">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="text-blue-600 text-xl">📧</div>
                      <div>
                        <div className="font-medium text-blue-800">Email Service Configuration</div>
                        <div className="text-sm text-blue-700 mt-1">
                          Configure SMTP settings to enable patient email functionality. 
                          For Gmail, use App Passwords instead of your regular password.
                        </div>
                      </div>
                    </div>
                  </div>

                  <form onSubmit={(e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    updateEmailConfig({
                      smtp_server: formData.get('smtp_server'),
                      smtp_port: parseInt(formData.get('smtp_port')),
                      smtp_username: formData.get('smtp_username'),
                      smtp_password: formData.get('smtp_password')
                    });
                  }}>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          SMTP Server
                        </label>
                        <input
                          type="text"
                          name="smtp_server"
                          defaultValue={configData.email.smtp_server}
                          placeholder="smtp.gmail.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          SMTP Port
                        </label>
                        <input
                          type="number"
                          name="smtp_port"
                          defaultValue={configData.email.smtp_port}
                          placeholder="587"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Email Address
                        </label>
                        <input
                          type="email"
                          name="smtp_username"
                          defaultValue={configData.email.smtp_username}
                          placeholder="your-email@gmail.com"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Password / App Password
                        </label>
                        <input
                          type="password"
                          name="smtp_password"
                          placeholder="Enter password or app password"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          required
                        />
                      </div>
                    </div>

                    <div className="flex gap-3 mt-6">
                      <button
                        type="submit"
                        disabled={configLoading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        {configLoading ? 'Saving...' : 'Save Configuration'}
                      </button>
                      <button
                        type="button"
                        onClick={testEmailConfig}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        Send Test Email
                      </button>
                    </div>
                  </form>

                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <div className="text-sm text-yellow-800">
                      <div className="font-medium mb-2">📋 Gmail Setup Instructions:</div>
                      <ol className="list-decimal list-inside space-y-1">
                        <li>Go to your Google Account settings</li>
                        <li>Enable 2-Step Verification</li>
                        <li>Generate an App Password at: myaccount.google.com/apppasswords</li>
                        <li>Use the generated App Password (not your regular password)</li>
                      </ol>
                    </div>
                  </div>
                </div>
              )}

              {/* Dentrix Configuration Tab */}
              {configActiveTab === 'dentrix' && (
                <div className="space-y-6">
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="text-purple-600 text-xl">🦷</div>
                      <div>
                        <div className="font-medium text-purple-800">Dentrix API Configuration</div>
                        <div className="text-sm text-purple-700 mt-1">
                          Configure Dentrix API credentials to enable patient lookup functionality.
                        </div>
                      </div>
                    </div>
                  </div>

                  <form onSubmit={(e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    updateDentrixConfig({
                      api_url: formData.get('api_url'),
                      api_key: formData.get('api_key')
                    });
                  }}>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Dentrix API URL
                        </label>
                        <input
                          type="url"
                          name="api_url"
                          defaultValue={configData.dentrix.api_url}
                          placeholder="https://api.dentrix.com/v1"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          API Key
                        </label>
                        <input
                          type="password"
                          name="api_key"
                          placeholder="Enter your Dentrix API key"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                          required
                        />
                      </div>
                    </div>

                    <div className="flex gap-3 mt-6">
                      <button
                        type="submit"
                        disabled={configLoading}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                      >
                        {configLoading ? 'Saving...' : 'Save Configuration'}
                      </button>
                      <button
                        type="button"
                        onClick={testDentrixConfig}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        Test Connection
                      </button>
                    </div>
                  </form>

                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <div className="text-sm text-yellow-800">
                      <div className="font-medium mb-2">📞 Getting Dentrix API Access:</div>
                      <ul className="list-disc list-inside space-y-1">
                        <li>Contact your Dentrix support representative</li>
                        <li>Request API credentials for patient lookup</li>
                        <li>Ensure you have proper licensing for API access</li>
                        <li>Verify HIPAA compliance requirements</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* AI Training Tab */}
              {configActiveTab === 'ai-training' && (
                <div className="space-y-6">
                  <div className="bg-indigo-50 p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="text-indigo-600 text-xl">🧠</div>
                      <div>
                        <h3 className="font-medium text-indigo-900">AI Training & Knowledge Base</h3>
                        <p className="text-sm text-indigo-700 mt-1">
                          Chat with your AI to improve its performance and add knowledge articles for reference.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* AI Chat Training */}
                  <div className="bg-white border rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-4">💬 Train Your AI Assistant</h4>
                    
                    <div className="border rounded-lg h-96 flex flex-col">
                      {/* Chat Messages */}
                      <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
                        {chatMessages.length === 0 ? (
                          <div className="text-center text-gray-500 mt-20">
                            <div className="text-4xl mb-2">🤖</div>
                            <p>Start a conversation to train your AI scribe</p>
                            <p className="text-sm mt-1">Ask questions, give feedback, or provide guidance</p>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {chatMessages.map((message, index) => (
                              <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                  message.role === 'user' 
                                    ? 'bg-blue-500 text-white' 
                                    : 'bg-white border shadow-sm'
                                }`}>
                                  <p className="text-sm">{message.content}</p>
                                  <p className="text-xs mt-1 opacity-70">
                                    {new Date(message.timestamp).toLocaleTimeString()}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Chat Input */}
                      <div className="border-t p-4 bg-white">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && sendTrainingMessage()}
                            placeholder="Type your message to train the AI..."
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                            disabled={isTrainingChat}
                          />
                          <button
                            onClick={sendTrainingMessage}
                            disabled={isTrainingChat || !chatInput.trim()}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                          >
                            {isTrainingChat ? '...' : 'Send'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Knowledge Articles */}
                  <div className="bg-white border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="font-medium text-gray-900">📚 Knowledge Base Articles</h4>
                      <button
                        onClick={() => setShowArticleEditor(true)}
                        className="px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                      >
                        + Add Article
                      </button>
                    </div>

                    {knowledgeArticles.length === 0 ? (
                      <div className="text-center text-gray-500 py-8">
                        <div className="text-3xl mb-2">📖</div>
                        <p>No knowledge articles yet</p>
                        <p className="text-sm mt-1">Add articles to help your AI provide better responses</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {knowledgeArticles.map((article, index) => (
                          <div key={index} className="border rounded-lg p-3 hover:bg-gray-50">
                            <div className="flex justify-between items-start">
                              <div>
                                <h5 className="font-medium text-gray-900">{article.title}</h5>
                                <p className="text-sm text-gray-600 mt-1">{article.category}</p>
                                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{article.content}</p>
                              </div>
                              <button
                                onClick={() => deleteKnowledgeArticle(article.id)}
                                className="text-red-500 hover:text-red-700 text-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Knowledge Article Editor Modal */}
      {showArticleEditor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold">Add Knowledge Article</h3>
                <button
                  onClick={() => setShowArticleEditor(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={createKnowledgeArticle} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Article Title
                  </label>
                  <input
                    type="text"
                    value={newArticle.title}
                    onChange={(e) => setNewArticle({...newArticle, title: e.target.value})}
                    placeholder="e.g., Post-Operative Care Instructions"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Category
                  </label>
                  <select
                    value={newArticle.category}
                    onChange={(e) => setNewArticle({...newArticle, category: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    required
                  >
                    <option value="">Select a category</option>
                    <option value="treatment">Treatment Guidelines</option>
                    <option value="post-care">Post-Operative Care</option>
                    <option value="diagnosis">Diagnosis Protocols</option>
                    <option value="billing">Billing & Coding</option>
                    <option value="general">General Information</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Content
                  </label>
                  <textarea
                    value={newArticle.content}
                    onChange={(e) => setNewArticle({...newArticle, content: e.target.value})}
                    placeholder="Enter the detailed content of the knowledge article..."
                    rows={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                  >
                    Save Article
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowArticleEditor(false)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Delete Session Confirmation Modal */}
      {showDeleteModal && sessionToDelete && (
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
                  <p className="text-red-700 text-sm">ID: {sessionToDelete.session_id}</p>
                  <p className="text-red-700 text-sm">Date: {sessionToDelete.timestamp ? new Date(sessionToDelete.timestamp).toLocaleDateString() : 'N/A'}</p>
                  <p className="text-red-700 text-sm">Provider: {sessionToDelete.doctor || 'N/A'}</p>
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
                    setSessionToDelete(null);
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

      {/* View All Memories Modal */}
      {showAllMemories && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex justify-between items-center">
                <h3 className="text-2xl font-semibold">AI Memory Management</h3>
                <button
                  onClick={() => setShowAllMemories(false)}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h4 className="text-lg font-semibold">AI Knowledge Base</h4>
                  <p className="text-gray-600">View and manage the AI model's learned information</p>
                </div>
                <div className="text-sm text-gray-500">
                  {aiMemories.length} Memory Items
                </div>
              </div>
              
              <div className="space-y-3">
                {aiMemories.map(memory => (
                  <div key={memory.id} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h5 className="font-medium text-lg">{memory.title}</h5>
                        <p className="text-gray-600 text-sm mt-1">Added {memory.addedDate}</p>
                        <div className="mt-2 text-sm text-gray-700">
                          This memory contains learned information about {memory.title.toLowerCase()} that helps the AI provide better responses during consultations.
                        </div>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => {
                            setEditingMemory(memory);
                            setShowMemoryEditor(true);
                          }}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => deleteMemory(memory.id)}
                          className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                
                {aiMemories.length === 0 && (
                  <div className="text-center py-12 text-gray-500">
                    <div className="text-4xl mb-4">🧠</div>
                    <p>No AI memories found</p>
                    <p className="text-sm mt-2">The AI model hasn't learned any specific information yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;