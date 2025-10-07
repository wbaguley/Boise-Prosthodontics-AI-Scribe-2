import React, { useState, useEffect } from 'react';
import { logout, getCurrentUser } from '../services/auth';
import Scribe from '../components/Scribe';
import axios from 'axios';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userData = await getCurrentUser();
        setUser(userData);
        
        const notesResponse = await axios.get('/notes/');
        setNotes(notesResponse.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleLogout = () => {
    logout();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                AI Scribe Dashboard
              </h1>
              <p className="text-sm text-gray-600">
                Welcome back, {user?.username}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Scribe Component */}
            <div className="lg:col-span-2">
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    AI Scribe
                  </h3>
                  <Scribe />
                </div>
              </div>
            </div>

            {/* Recent Notes */}
            <div className="lg:col-span-1">
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    Recent Notes
                  </h3>
                  <div className="space-y-3">
                    {notes.length === 0 ? (
                      <p className="text-gray-500 text-sm">No notes yet</p>
                    ) : (
                      notes.slice(0, 5).map((note) => (
                        <div
                          key={note.id}
                          className="border-l-4 border-blue-400 pl-4 py-2"
                        >
                          <p className="text-sm font-medium text-gray-900">
                            {note.title}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(note.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
