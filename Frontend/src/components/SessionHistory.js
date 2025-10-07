import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

const SessionHistory = ({ onNavigate }) => {
  const [sessions, setSessions] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [sessionsPerPage] = useState(20);

  useEffect(() => {
    fetchSessions();
    fetchProviders();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [sessions, searchTerm, selectedProvider, startDate, endDate]);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/sessions`);
      if (response.ok) {
        const data = await response.json();
        // Sort by timestamp, newest first
        const sortedSessions = data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setSessions(sortedSessions);
      } else {
        setError('Failed to load sessions');
      }
    } catch (err) {
      setError('Failed to load sessions');
      console.error('Error fetching sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/providers`);
      if (response.ok) {
        const data = await response.json();
        setProviders(data);
      }
    } catch (err) {
      console.error('Error fetching providers:', err);
    }
  };

  const applyFilters = () => {
    let filtered = [...sessions];

    // Search filter - searches in session ID, doctor name, transcript, and SOAP note
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(session => 
        session.session_id?.toLowerCase().includes(search) ||
        session.doctor?.toLowerCase().includes(search) ||
        session.transcript?.toLowerCase().includes(search) ||
        session.soap_note?.toLowerCase().includes(search)
      );
    }

    // Provider filter
    if (selectedProvider) {
      filtered = filtered.filter(session => 
        session.doctor === selectedProvider || session.provider_id?.toString() === selectedProvider
      );
    }

    // Date range filter
    if (startDate) {
      filtered = filtered.filter(session => {
        const sessionDate = new Date(session.timestamp);
        const filterDate = new Date(startDate);
        return sessionDate >= filterDate;
      });
    }

    if (endDate) {
      filtered = filtered.filter(session => {
        const sessionDate = new Date(session.timestamp);
        const filterDate = new Date(endDate + 'T23:59:59'); // Include the entire end date
        return sessionDate <= filterDate;
      });
    }

    setFilteredSessions(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedProvider('');
    setStartDate('');
    setEndDate('');
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatTemplateName = (template) => {
    if (!template) return 'Default';
    return template.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const truncateText = (text, maxLength = 150) => {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  const exportToCSV = () => {
    const csvHeaders = ['Session ID', 'Doctor', 'Date', 'Template', 'Transcript Preview', 'SOAP Preview'];
    const csvData = filteredSessions.map(session => [
      session.session_id,
      session.doctor,
      formatDate(session.timestamp),
      formatTemplateName(session.template_used),
      `"${(session.transcript || '').replace(/"/g, '""').substring(0, 100)}"`,
      `"${(session.soap_note || '').replace(/"/g, '""').substring(0, 100)}"`
    ]);

    const csvContent = [csvHeaders, ...csvData]
      .map(row => row.join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `session-history-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  // Pagination logic
  const indexOfLastSession = currentPage * sessionsPerPage;
  const indexOfFirstSession = indexOfLastSession - sessionsPerPage;
  const currentSessions = filteredSessions.slice(indexOfFirstSession, indexOfLastSession);
  const totalPages = Math.ceil(filteredSessions.length / sessionsPerPage);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading session history...</p>
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
                  ← Back to Dashboard
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-800">Session History</h1>
                  <p className="text-sm text-gray-600">
                    {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''} found
                  </p>
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={exportToCSV}
                disabled={filteredSessions.length === 0}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                📊 Export CSV
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Filters */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Filters</h2>
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear All Filters
            </button>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search
              </label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search sessions, doctors, content..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Provider Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Provider
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Providers</option>
                {providers.map(provider => (
                  <option key={provider.id} value={provider.name}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Start Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* End Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                To Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Active Filters Summary */}
          {(searchTerm || selectedProvider || startDate || endDate) && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex flex-wrap gap-2">
                <span className="text-sm text-gray-600">Active filters:</span>
                {searchTerm && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    Search: "{searchTerm}"
                  </span>
                )}
                {selectedProvider && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    Provider: {selectedProvider}
                  </span>
                )}
                {startDate && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    From: {new Date(startDate).toLocaleDateString()}
                  </span>
                )}
                {endDate && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    To: {new Date(endDate).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sessions List */}
        <div className="bg-white rounded-xl shadow-lg">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold">
              Sessions ({filteredSessions.length})
            </h2>
          </div>

          {currentSessions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {filteredSessions.length === 0 ? (
                sessions.length === 0 ? (
                  <>
                    <p>No sessions found.</p>
                    <p className="text-sm mt-2">Start recording sessions to see them here.</p>
                  </>
                ) : (
                  <>
                    <p>No sessions match your filters.</p>
                    <p className="text-sm mt-2">Try adjusting your search criteria.</p>
                  </>
                )
              ) : (
                <p>No sessions to display on this page.</p>
              )}
            </div>
          ) : (
            <>
              <div className="divide-y divide-gray-200">
                {currentSessions.map((session) => (
                  <div
                    key={session.session_id}
                    onClick={() => onNavigate && onNavigate('session-detail', session.session_id)}
                    className="p-6 hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {session.doctor || 'Unknown Provider'}
                        </h3>
                        <div className="text-sm text-gray-600 flex items-center gap-4">
                          <span>{formatDate(session.timestamp)}</span>
                          <span>•</span>
                          <span>ID: {session.session_id}</span>
                          <span>•</span>
                          <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                            {formatTemplateName(session.template_used)}
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-blue-600 font-medium">
                        Click to view →
                      </div>
                    </div>
                    
                    {session.transcript && (
                      <div className="mb-2">
                        <div className="text-xs font-medium text-gray-700 mb-1">Transcript:</div>
                        <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          {truncateText(session.transcript)}
                        </div>
                      </div>
                    )}
                    
                    {session.soap_note && (
                      <div>
                        <div className="text-xs font-medium text-gray-700 mb-1">SOAP Note:</div>
                        <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                          {truncateText(session.soap_note)}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="p-6 border-t border-gray-200">
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-600">
                      Showing {indexOfFirstSession + 1}-{Math.min(indexOfLastSession, filteredSessions.length)} of {filteredSessions.length} sessions
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      
                      {/* Page numbers */}
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (currentPage <= 3) {
                          pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = currentPage - 2 + i;
                        }
                        
                        return (
                          <button
                            key={pageNum}
                            onClick={() => setCurrentPage(pageNum)}
                            className={`px-3 py-1 border rounded ${
                              currentPage === pageNum
                                ? 'bg-blue-500 text-white border-blue-500'
                                : 'border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                      
                      <button
                        onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionHistory;