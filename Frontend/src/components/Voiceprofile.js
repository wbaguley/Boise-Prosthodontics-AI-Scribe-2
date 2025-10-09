import React, { useState, useRef } from 'react';

const API_URL = process.env.REACT_APP_API_URL || '';

const VoiceProfile = ({ doctorName, onClose, onSave }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [currentPhrase, setCurrentPhrase] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const trainingPhrases = [
    "Good morning, how are you feeling today?",
    "Let me examine that area for you.",
    "I can see some inflammation around the tooth.",
    "We need to take an X-ray to get a better look.",
    "I recommend we proceed with the treatment plan."
  ];

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      });
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const newRecordings = [...recordings];
        newRecordings[currentPhrase] = audioBlob;
        setRecordings(newRecordings);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start(100);
      setIsRecording(true);
    } catch (error) {
      console.error('Recording error:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const playRecording = (index) => {
    if (recordings[index]) {
      const audio = new Audio(URL.createObjectURL(recordings[index]));
      audio.play();
    }
  };

  const deleteRecording = (index) => {
    const newRecordings = [...recordings];
    newRecordings[index] = null;
    setRecordings(newRecordings);
  };

  const nextPhrase = () => {
    if (currentPhrase < trainingPhrases.length - 1) {
      setCurrentPhrase(currentPhrase + 1);
    }
  };

  const prevPhrase = () => {
    if (currentPhrase > 0) {
      setCurrentPhrase(currentPhrase - 1);
    }
  };

  const saveProfile = async () => {
    const validRecordings = recordings.filter(r => r !== null && r !== undefined);
    
    if (validRecordings.length < 3) {
      alert('Please record at least 3 voice samples');
      return;
    }

    setIsUploading(true);
    setUploadProgress('Preparing voice samples...');

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('doctor_name', doctorName);
      
      // Add all recordings
      recordings.forEach((recording, index) => {
        if (recording) {
          formData.append('files', recording, `sample_${index}.webm`);
        }
      });

      setUploadProgress('Uploading to server...');

      const response = await fetch(`${API_URL}/api/voice-profile`, {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        const result = await response.json();
        setUploadProgress(`Success! Created profile with ${result.samples} samples`);
        
        setTimeout(() => {
          onSave();
          onClose();
        }, 1500);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save voice profile');
      }
    } catch (error) {
      console.error('Error saving voice profile:', error);
      alert(`Error: ${error.message}`);
      setUploadProgress('');
      setIsUploading(false);
    }
  };

  const recordedCount = recordings.filter(r => r !== null && r !== undefined).length;
  const progress = (recordedCount / trainingPhrases.length) * 100;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-[500px] max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold">
              Voice Training for {doctorName}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Record at least 3 phrases for accurate speaker identification
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-gray-500 hover:text-gray-700 text-xl"
          >
            ×
          </button>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{recordedCount} of {trainingPhrases.length} recorded</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
        
        {/* Current Phrase */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <p className="text-sm font-medium text-gray-700">
              Phrase {currentPhrase + 1} of {trainingPhrases.length}
            </p>
            {recordings[currentPhrase] && (
              <button
                onClick={() => playRecording(currentPhrase)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                🔊 Play
              </button>
            )}
          </div>
          
          <div className="bg-blue-50 p-4 rounded-lg mb-3">
            <p className="text-center font-medium text-gray-800">
              "{trainingPhrases[currentPhrase]}"
            </p>
          </div>

          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isUploading}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-all ${
              isRecording 
                ? 'bg-red-500 text-white hover:bg-red-600' 
                : 'bg-blue-500 text-white hover:bg-blue-600'
            } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isRecording ? '⏹️ Stop Recording' : 
             recordings[currentPhrase] ? '🔄 Re-record This Phrase' : '🎤 Record This Phrase'}
          </button>
          
          {recordings[currentPhrase] && (
            <div className="mt-2 flex items-center justify-between text-sm">
              <span className="text-green-600">✓ Recorded</span>
              <button
                onClick={() => deleteRecording(currentPhrase)}
                className="text-red-600 hover:text-red-700"
              >
                Delete
              </button>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between mb-6">
          <button
            onClick={prevPhrase}
            disabled={currentPhrase === 0 || isUploading}
            className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Previous
          </button>
          <button
            onClick={nextPhrase}
            disabled={currentPhrase === trainingPhrases.length - 1 || isUploading}
            className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>

        {/* All Phrases Overview */}
        <div className="mb-6 p-3 bg-gray-50 rounded">
          <p className="text-sm font-medium text-gray-700 mb-2">Recording Status:</p>
          <div className="grid grid-cols-5 gap-2">
            {trainingPhrases.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentPhrase(index)}
                disabled={isUploading}
                className={`h-10 rounded flex items-center justify-center text-sm font-medium ${
                  currentPhrase === index 
                    ? 'bg-blue-500 text-white ring-2 ring-blue-300' 
                    : recordings[index]
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {index + 1}
                {recordings[index] && ' ✓'}
              </button>
            ))}
          </div>
        </div>

        {/* Upload Progress */}
        {uploadProgress && (
          <div className="mb-4 p-3 bg-blue-50 text-blue-700 rounded text-center">
            {uploadProgress}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="flex-1 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={saveProfile}
            disabled={recordedCount < 3 || isUploading}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? 'Saving...' : `Save Profile (${recordedCount}/5)`}
          </button>
        </div>

        <p className="text-xs text-gray-500 mt-3 text-center">
          💡 Tip: Speak naturally and clearly. Record in a quiet environment for best results.
        </p>
      </div>
    </div>
  );
};

export default VoiceProfile;