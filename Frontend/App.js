import React, { useState, useRef, useEffect } from 'react';

const App = () => {
  const [transcript, setTranscript] = useState('');
  const [soap, setSoap] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [audioUrl, setAudioUrl] = useState(null);
  const websocket = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunks = useRef([]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    websocket.current = new WebSocket('ws://localhost:4001/ws/audio');
    
    websocket.current.onopen = () => {
      console.log('WebSocket connected');
      setStatus('Connected');
    };
    
    websocket.current.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        // Audio data received
        const audioBlob = new Blob([event.data], { type: 'audio/wav' });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
        
        // Auto-play the audio
        const audio = new Audio(url);
        audio.volume = 0.7;
        audio.play().catch(e => console.log('Audio playback error:', e));
      } else {
        // JSON message
        try {
          const data = JSON.parse(event.data);
          if (data.transcript) setTranscript(data.transcript);
          if (data.soap) setSoap(data.soap);
          if (data.status) setStatus(data.status);
          if (data.error) {
            setStatus(`Error: ${data.error}`);
            console.error('Server error:', data.error);
          }
        } catch (e) {
          console.error('Message parse error:', e);
        }
      }
    };
    
    websocket.current.onclose = () => {
      console.log('WebSocket closed');
      setStatus('Disconnected - Refresh to reconnect');
    };
    
    websocket.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('Connection error');
    };
  };

  const startRecording = async (duration = 30000) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      audioChunks.current = [];
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.current.push(e.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        
        // Convert to WAV and send
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioData = new Uint8Array(arrayBuffer);
        
        if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
          // Send audio data in chunks
          const chunkSize = 64 * 1024; // 64KB chunks
          for (let i = 0; i < audioData.length; i += chunkSize) {
            const chunk = audioData.slice(i, i + chunkSize);
            websocket.current.send(chunk);
            await new Promise(resolve => setTimeout(resolve, 10)); // Small delay between chunks
          }
          websocket.current.send('END');
        }
        
        setIsRecording(false);
        setStatus('Processing audio...');
      };
      
      mediaRecorderRef.current.start(1000); // Collect data every second
      setIsRecording(true);
      setStatus(`Recording... (${duration/1000}s)`);
      
      // Auto-stop after duration
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, duration);
      
    } catch (error) {
      console.error('Recording error:', error);
      setStatus('Microphone access denied');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setStatus('Copied to clipboard!');
      setTimeout(() => setStatus('Ready'), 2000);
    }).catch(err => {
      console.error('Copy failed:', err);
      setStatus('Copy failed - please select and copy manually');
    });
  };

  const playAudio = () => {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-6xl mx-auto">
        <header className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Boise Prosthodontics AI Scribe
          </h1>
          <p className="text-gray-600">HIPAA-compliant local transcription & SOAP notes</p>
          <div className="mt-4 flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${
              status.includes('Connected') ? 'bg-green-500' : 
              status.includes('Error') ? 'bg-red-500' : 'bg-yellow-500'
            }`}></div>
            <span className="text-sm text-gray-700">{status}</span>
          </div>
        </header>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Control Panel */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Recording Controls</h2>
            
            <div className="space-y-4">
              <button
                onClick={() => startRecording(30000)}
                disabled={isRecording}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                  isRecording 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700 transform hover:scale-105'
                }`}
              >
                {isRecording ? '🔴 Recording...' : '🎤 Start Session (30s)'}
              </button>
              
              <button
                onClick={() => startRecording(10000)}
                disabled={isRecording}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                  isRecording 
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                    : 'bg-green-600 text-white hover:bg-green-700 transform hover:scale-105'
                }`}
              >
                {isRecording ? '🔴 Recording...' : '✏️ Quick Correction (10s)'}
              </button>
              
              {isRecording && (
                <button
                  onClick={stopRecording}
                  className="w-full py-3 px-6 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-all"
                >
                  ⏹️ Stop Recording
                </button>
              )}
              
              {audioUrl && (
                <button
                  onClick={playAudio}
                  className="w-full py-3 px-6 rounded-lg font-medium bg-purple-600 text-white hover:bg-purple-700 transition-all"
                >
                  🔊 Play SOAP Summary
                </button>
              )}
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-medium text-gray-700 mb-2">Quick Guide:</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Click "Start Session" to record consultation</li>
                <li>• AI identifies Doctor vs Patient speakers</li>
                <li>• Auto-generates SOAP note format</li>
                <li>• Edit as needed, then copy to EHR</li>
                <li>• Use "Quick Correction" for additions</li>
              </ul>
            </div>
          </div>

          {/* Transcript Panel */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800">Transcript</h2>
              <button
                onClick={() => copyToClipboard(transcript)}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-all text-sm"
              >
                📋 Copy
              </button>
            </div>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              className="w-full h-64 p-4 border border-gray-300 rounded-lg font-mono text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Diarized transcript will appear here..."
            />
          </div>
        </div>

        {/* SOAP Note Panel */}
        <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-800">SOAP Note</h2>
            <div className="space-x-2">
              <button
                onClick={() => copyToClipboard(soap)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-all"
              >
                📋 Copy to EHR
              </button>
              <button
                onClick={() => {
                  const blob = new Blob([soap], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `SOAP_${new Date().toISOString().split('T')[0]}.txt`;
                  a.click();
                }}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-all"
              >
                💾 Save
              </button>
            </div>
          </div>
          <textarea
            value={soap}
            onChange={(e) => setSoap(e.target.value)}
            className="w-full h-96 p-4 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="SOAP note will be generated here...

SUBJECTIVE:
- Chief complaint
- History of present illness
- Review of systems

OBJECTIVE:
- Clinical findings
- Vital signs
- Test results

ASSESSMENT:
- Diagnosis
- Differential diagnosis

PLAN:
- Treatment plan
- Follow-up
- Patient education"
          />
        </div>

        <footer className="mt-8 text-center text-sm text-gray-600">
          <p>© 2024 Boise Prosthodontics | HIPAA-Compliant Local Processing | No Cloud Storage</p>
          <p className="mt-2">⚠️ Remember to delete logs monthly from logs/scribe_logs.txt</p>
        </footer>
      </div>
    </div>
  );
};

export default App;