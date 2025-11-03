import React, { useState } from 'react';
import { Search, Send, CheckCircle, AlertCircle, User, Calendar, FileText } from 'lucide-react';

const DentrixIntegration = ({ sessionId, soapNote, providerId }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [searching, setSearching] = useState(false);

  const searchPatients = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a patient name or chart number');
      return;
    }

    setSearching(true);
    setError('');
    setPatients([]);
    setSelectedPatient(null);

    try {
      const response = await fetch(
        `/api/dentrix/patients/search?query=${encodeURIComponent(searchQuery)}`
      );

      if (!response.ok) {
        throw new Error('Failed to search patients');
      }

      const data = await response.json();

      if (data.success && data.patients) {
        setPatients(data.patients);
        if (data.patients.length === 0) {
          setError('No patients found matching your search');
        }
      } else {
        throw new Error(data.error || 'Search failed');
      }
    } catch (err) {
      setError(`Search failed: ${err.message}`);
      console.error('Patient search error:', err);
    } finally {
      setSearching(false);
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient);
    setError('');
  };

  const sendToDentrix = async () => {
    if (!selectedPatient) {
      setError('Please select a patient first');
      return;
    }

    setSending(true);
    setError('');

    try {
      const response = await fetch(`/api/sessions/${sessionId}/send-to-dentrix`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_id: selectedPatient.patient_id,
          provider_id: parseInt(providerId) || 1,
          note_type: 'SOAP',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send SOAP note to Dentrix');
      }

      const data = await response.json();

      if (data.success) {
        setSent(true);
        setError('');
      } else if (data.already_sent) {
        setSent(true);
        setError('Note: This SOAP note was already sent to Dentrix');
      } else {
        throw new Error(data.message || 'Failed to send to Dentrix');
      }
    } catch (err) {
      setError(`Failed to send: ${err.message}`);
      console.error('Send to Dentrix error:', err);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      searchPatients();
    }
  };

  if (sent) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6">
        <div className="flex items-center gap-3 text-green-700">
          <CheckCircle className="w-6 h-6" />
          <div>
            <h3 className="font-semibold text-lg">SOAP Note Sent to Dentrix!</h3>
            <p className="text-sm mt-1">
              Successfully posted to patient: {selectedPatient?.name || 'Unknown'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <div className="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          Send to Dentrix
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Search for patient and post SOAP note to their chart
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Search Section */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Patient
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter patient name or chart number..."
                className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={searching}
              />
              <Search className="absolute right-3 top-2.5 w-5 h-5 text-gray-400" />
            </div>
            <button
              onClick={searchPatients}
              disabled={searching || !searchQuery.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {searching ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Searching...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Search
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="flex items-start gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Patient Results */}
        {patients.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Results ({patients.length} found)
            </label>
            <div className="border border-gray-200 rounded-lg divide-y divide-gray-200 max-h-64 overflow-y-auto">
              {patients.map((patient) => (
                <div
                  key={patient.patient_id}
                  onClick={() => selectPatient(patient)}
                  className={`p-4 cursor-pointer transition-colors hover:bg-blue-50 ${
                    selectedPatient?.patient_id === patient.patient_id
                      ? 'bg-blue-100 border-l-4 border-blue-600'
                      : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <User className="w-5 h-5 text-gray-400 mt-0.5" />
                      <div>
                        <p className="font-medium text-gray-900">{patient.name}</p>
                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                          {patient.dob && (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              DOB: {patient.dob}
                            </span>
                          )}
                          {patient.chart_number && (
                            <span>Chart: {patient.chart_number}</span>
                          )}
                        </div>
                        {patient.phone && (
                          <p className="text-sm text-gray-500 mt-1">
                            Phone: {patient.phone}
                          </p>
                        )}
                      </div>
                    </div>
                    {selectedPatient?.patient_id === patient.patient_id && (
                      <CheckCircle className="w-5 h-5 text-blue-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Selected Patient Summary */}
        {selectedPatient && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-900 mb-2">
              Selected Patient
            </h4>
            <div className="space-y-1 text-sm text-blue-800">
              <p><strong>Name:</strong> {selectedPatient.name}</p>
              {selectedPatient.dob && (
                <p><strong>DOB:</strong> {selectedPatient.dob}</p>
              )}
              {selectedPatient.chart_number && (
                <p><strong>Chart #:</strong> {selectedPatient.chart_number}</p>
              )}
            </div>
          </div>
        )}

        {/* Send Button */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            {selectedPatient ? (
              <span className="text-green-600 font-medium">
                ✓ Patient selected - ready to send
              </span>
            ) : (
              <span>Search and select a patient to continue</span>
            )}
          </div>
          <button
            onClick={sendToDentrix}
            disabled={!selectedPatient || sending}
            className="px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-medium"
          >
            {sending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Sending to Dentrix...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Send to Dentrix
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DentrixIntegration;
