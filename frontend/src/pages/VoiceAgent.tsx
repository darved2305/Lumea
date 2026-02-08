import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  MicOff,
  PhoneOff,
  Phone,
  Volume2,
  VolumeX,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  User,
  Activity,
  Heart,
  Pill,
  Moon,
} from 'lucide-react';
import DashboardNavbar from '../components/dashboard/DashboardNavbar';
import { API_BASE_URL } from '../config/api';
import { getAuthToken } from '../utils/auth';
import speechService, { SpeechRecognitionResult } from '../services/speechService';
import './VoiceAgent.css';

type CallState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

interface ContextSummary {
  name?: string;
  age?: number;
  gender?: string;
  bmi?: number;
  conditions?: string[];
  medications?: string[];
  allergies?: string[];
  sleep_hours?: number;
  exercise_frequency?: string;
  reports_count?: number;
}

interface VoiceContext {
  profile_complete: boolean;
  has_personalization?: boolean;
  summary: ContextSummary;
}

// Premium Flowing Orb SVG Component with animated turbulence
function FlowingOrb({ state }: { state: CallState }) {
  const getGradientColors = () => {
    switch (state) {
      case 'listening':
        return { c1: '#5da47a', c2: '#7ac19a', c3: '#3d8f5a' };
      case 'thinking':
        return { c1: '#7a9cc6', c2: '#9bb8d8', c3: '#5a7faa' };
      case 'speaking':
        return { c1: '#8b7ac6', c2: '#a898d8', c3: '#6b5aaa' };
      default:
        return { c1: '#6b9175', c2: '#8fb199', c3: '#4a7c59' };
    }
  };

  const colors = getGradientColors();
  const turbulenceFreq = state === 'speaking' ? '0.015' : state === 'listening' ? '0.012' : '0.008';
  const animDur = state === 'speaking' ? '2s' : state === 'listening' ? '3s' : '6s';

  return (
    <svg className="orb-svg" viewBox="0 0 200 200">
      <defs>
        {/* Animated turbulence filter for flowing effect */}
        <filter id="orbFlow" x="-50%" y="-50%" width="200%" height="200%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency={turbulenceFreq}
            numOctaves="3"
            result="noise"
          >
            <animate
              attributeName="baseFrequency"
              dur={animDur}
              values={`${turbulenceFreq};${parseFloat(turbulenceFreq) * 1.5};${turbulenceFreq}`}
              repeatCount="indefinite"
            />
          </feTurbulence>
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="12"
            xChannelSelector="R"
            yChannelSelector="G"
          >
            <animate
              attributeName="scale"
              dur={animDur}
              values="12;18;12"
              repeatCount="indefinite"
            />
          </feDisplacementMap>
        </filter>

        {/* Radial gradient */}
        <radialGradient id="orbGradient" cx="35%" cy="35%" r="65%">
          <stop offset="0%" stopColor={colors.c2} />
          <stop offset="50%" stopColor={colors.c1} />
          <stop offset="100%" stopColor={colors.c3} />
        </radialGradient>

        {/* Highlight gradient */}
        <radialGradient id="orbHighlight" cx="30%" cy="30%" r="40%">
          <stop offset="0%" stopColor="white" stopOpacity="0.35" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Main orb circle with flowing filter */}
      <circle
        cx="100"
        cy="100"
        r="85"
        fill="url(#orbGradient)"
        filter="url(#orbFlow)"
      />

      {/* Highlight overlay */}
      <circle
        cx="100"
        cy="100"
        r="80"
        fill="url(#orbHighlight)"
      />
    </svg>
  );
}

function VoiceAgent() {
  const [callState, setCallState] = useState<CallState>('idle');
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [hasPersonalization, setHasPersonalization] = useState(false);
  const [contextSummary, setContextSummary] = useState<ContextSummary>({});
  const [userName, setUserName] = useState('User');
  const [error, setError] = useState<string | null>(null);
  const [ttsConfigured, setTtsConfigured] = useState<boolean | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isCallActiveRef = useRef(isCallActive);

  // Keep ref in sync with state
  useEffect(() => {
    isCallActiveRef.current = isCallActive;
  }, [isCallActive]);

  // Check TTS status on mount
  useEffect(() => {
    checkTtsStatus();
  }, []);

  const checkTtsStatus = async () => {
    try {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/voice/tts/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTtsConfigured(data.configured);
        if (!data.configured) {
          console.log('ElevenLabs not configured, will use browser TTS fallback', data);
        }
      }
    } catch (err) {
      console.error('Failed to check TTS status:', err);
      setTtsConfigured(false);
    }
  };

  // Fetch user context on mount
  useEffect(() => {
    fetchContext();
  }, []);

  // Handle speech recognition results
  const handleSpeechResult = useCallback((result: SpeechRecognitionResult) => {
    setCurrentTranscript(result.transcript);
    if (result.isFinal) {
      handleTranscriptComplete(result.transcript);
    }
  }, []);

  const handleSpeechError = useCallback((err: string) => {
    console.error('Speech recognition error:', err);
    if (err === 'no-speech') {
      setCallState('idle');
      setError('No speech detected. Please try again.');
    } else {
      setCallState('error');
      setError(`Speech recognition error: ${err}`);
    }
  }, []);

  // Check microphone permission and availability on mount
  useEffect(() => {
    const initSpeech = async () => {
      const available = await speechService.isAvailable();
      if (!available) {
        console.warn('Speech recognition not available');
      }

      const permission = await speechService.checkPermission();
      if (permission === 'prompt') {
        await speechService.requestPermission();
      }
    };

    initSpeech();

    return () => {
      speechService.abortListening();
    };
  }, []);

  const fetchContext = async () => {
    try {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/voice/context`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data: VoiceContext = await response.json();
        setHasPersonalization(data.has_personalization || false);
        setContextSummary(data.summary || {});
        setUserName(data.summary?.name || 'User');
      }
    } catch (err) {
      console.error('Failed to fetch context:', err);
    }
  };

  const startCall = useCallback(() => {
    setIsCallActive(true);
    setCallState('idle');
    setMessages([]);
    setError(null);
    setTimeout(() => startListening(), 500);
  }, []);

  const endCall = useCallback(() => {
    setIsCallActive(false);
    setCallState('idle');
    setCurrentTranscript('');

    speechService.stopListening();

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }, []);

  const startListening = useCallback(async () => {
    const available = await speechService.isAvailable();
    if (!available) {
      setError('Speech recognition not available in this browser.');
      return;
    }

    try {
      setCallState('listening');
      setCurrentTranscript('');
      setError(null);

      await speechService.startListening({
        onResult: handleSpeechResult,
        onError: handleSpeechError,
        onEnd: () => {
          if (isCallActiveRef.current && callState === 'listening') {
            // flow control
          }
        }
      });
    } catch (err) {
      console.error('Failed to start recognition:', err);
      setError('Failed to start listening. Please try again.');
      setCallState('idle');
    }
  }, [handleSpeechResult, handleSpeechError, callState]);

  const stopListening = useCallback(() => {
    speechService.stopListening();
  }, []);

  const handleTranscriptComplete = async (transcript: string) => {
    if (!transcript.trim()) {
      setCallState('idle');
      return;
    }

    const userMessage: Message = {
      role: 'user',
      text: transcript,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setCurrentTranscript('');

    await getAIResponse(transcript);
  };

  const getAIResponse = async (text: string) => {
    setCallState('thinking');

    try {
      const token = getAuthToken();

      const answerResponse = await fetch(`${API_BASE_URL}/api/voice/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ text }),
      });

      if (!answerResponse.ok) {
        throw new Error('Failed to get answer');
      }

      const answerData = await answerResponse.json();
      const answerText = answerData.answer_text;

      const assistantMessage: Message = {
        role: 'assistant',
        text: answerText,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      await convertToSpeech(answerText);

    } catch (err) {
      console.error('Error getting AI response:', err);
      setError('Failed to get response. Please try again.');
      setCallState('idle');
    }
  };

  const useBrowserTTS = (text: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (!('speechSynthesis' in window)) {
        reject(new Error('Browser TTS not supported'));
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = isSpeakerMuted ? 0 : 1;

      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v =>
        v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Samantha'))
      ) || voices.find(v => v.lang.startsWith('en')) || voices[0];

      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onend = () => resolve();
      utterance.onerror = (e) => reject(e);

      window.speechSynthesis.speak(utterance);
    });
  };

  const convertToSpeech = async (text: string) => {
    setCallState('speaking');

    // If ElevenLabs not configured, use browser TTS directly
    if (ttsConfigured === false) {
      console.log('Using browser TTS fallback (ElevenLabs not configured)');
      try {
        await useBrowserTTS(text);
      } catch (e) {
        console.error('Browser TTS failed:', e);
      }
      setCallState('idle');
      if (isCallActiveRef.current) {
        setTimeout(() => startListening(), 600);
      }
      return;
    }

    try {
      const token = getAuthToken();

      const ttsResponse = await fetch(`${API_BASE_URL}/api/voice/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ text }),
      });

      if (!ttsResponse.ok) {
        // If 503, fall back to browser TTS
        if (ttsResponse.status === 503) {
          console.log('ElevenLabs unavailable, falling back to browser TTS');
          try {
            await useBrowserTTS(text);
          } catch (e) {
            console.error('Browser TTS fallback failed:', e);
          }
          setCallState('idle');
          if (isCallActiveRef.current) {
            setTimeout(() => startListening(), 600);
          }
          return;
        }
        throw new Error('TTS conversion failed');
      }

      const audioBlob = await ttsResponse.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      if (isSpeakerMuted) {
        audio.volume = 0;
      }

      audio.onended = () => {
        setCallState('idle');
        URL.revokeObjectURL(audioUrl);
        if (isCallActiveRef.current) {
          setTimeout(() => startListening(), 600);
        }
      };

      audio.onerror = () => {
        setError('Failed to play audio');
        setCallState('idle');
      };

      await audio.play();

    } catch (err) {
      console.error('TTS error:', err);
      // Fallback to browser TTS on any error
      try {
        await useBrowserTTS(text);
      } catch (e) {
        console.error('Browser TTS fallback failed:', e);
      }
      setCallState('idle');
      if (isCallActiveRef.current) {
        setTimeout(() => startListening(), 600);
      }
    }
  };

  const toggleMic = () => {
    setIsMicMuted(!isMicMuted);
    if (isMicMuted) {
      startListening();
    } else {
      stopListening();
      setCallState('idle');
    }
  };

  const toggleSpeaker = () => {
    setIsSpeakerMuted(!isSpeakerMuted);
    if (audioRef.current) {
      audioRef.current.volume = isSpeakerMuted ? 1 : 0;
    }
  };

  const getStatusLabel = () => {
    switch (callState) {
      case 'listening':
        return 'Listening...';
      case 'thinking':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      default:
        return isCallActive ? 'Ready to listen' : 'Start a voice conversation';
    }
  };

  // Build context items for sidebar
  const contextItems = [];
  if (contextSummary.age && contextSummary.gender) {
    contextItems.push({
      icon: User,
      label: 'Demographics',
      value: `${contextSummary.age} years, ${contextSummary.gender}`,
    });
  }
  if (contextSummary.bmi) {
    contextItems.push({
      icon: Activity,
      label: 'BMI',
      value: contextSummary.bmi.toString(),
    });
  }
  if (contextSummary.conditions && contextSummary.conditions.length > 0) {
    contextItems.push({
      icon: Heart,
      label: 'Conditions',
      value: contextSummary.conditions.slice(0, 3).join(', '),
    });
  }
  if (contextSummary.medications && contextSummary.medications.length > 0) {
    contextItems.push({
      icon: Pill,
      label: 'Medications',
      value: contextSummary.medications.slice(0, 3).join(', '),
    });
  }
  if (contextSummary.sleep_hours) {
    contextItems.push({
      icon: Moon,
      label: 'Sleep',
      value: `${contextSummary.sleep_hours} hours/night`,
    });
  }

  return (
    <div className="voice-agent-page">
      <DashboardNavbar userName={userName} userStatus="" />

      <div className="voice-agent-content">
        <div className="voice-agent-container">
          {/* Page Header */}
          <div className="voice-agent-header">
            <h1>Voice Agent</h1>
            <p>Talk to Lumea about your health — get personalized insights based on your profile</p>
          </div>

          {/* Main Grid */}
          <div className="voice-agent-grid">
            {/* Left: Voice Call Card */}
            <div className="voice-card">
              <div className="voice-card-header">
                <div className="voice-card-title">
                  <div className="voice-card-header-icon">
                    <Phone size={20} />
                  </div>
                  <h2>Voice Conversation</h2>
                </div>
                {isCallActive && (
                  <button
                    className="transcript-toggle-btn"
                    onClick={() => setShowTranscript(!showTranscript)}
                  >
                    <MessageSquare size={14} />
                    {showTranscript ? 'Hide' : 'Transcript'}
                  </button>
                )}
              </div>

              {/* Orb Section - Always shown */}
              <div className="orb-section">
                {/* Flowing Orb */}
                <div className={`orb-wrapper ${callState}`}>
                  <div className="orb-glow" />
                  <div className="orb-ring" />
                  <FlowingOrb state={callState} />
                </div>

                {/* Status */}
                <div className="orb-status">
                  <div className="orb-status-label">{getStatusLabel()}</div>
                  {currentTranscript && (
                    <div className="orb-status-transcript">"{currentTranscript}"</div>
                  )}
                </div>

                {/* Controls */}
                <div className="call-controls">
                  {!isCallActive ? (
                    <motion.button
                      className="call-btn call-btn-primary"
                      onClick={startCall}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <Phone size={18} />
                      Call AI Agent
                    </motion.button>
                  ) : (
                    <>
                      <button
                        className={`control-btn ${isMicMuted ? 'muted' : ''}`}
                        onClick={toggleMic}
                        title={isMicMuted ? 'Unmute' : 'Mute'}
                      >
                        {isMicMuted ? <MicOff size={18} /> : <Mic size={18} />}
                      </button>

                      <motion.button
                        className="call-btn call-btn-end"
                        onClick={endCall}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                      >
                        <PhoneOff size={16} />
                        End Call
                      </motion.button>

                      <button
                        className={`control-btn ${isSpeakerMuted ? 'muted' : ''}`}
                        onClick={toggleSpeaker}
                        title={isSpeakerMuted ? 'Unmute speaker' : 'Mute speaker'}
                      >
                        {isSpeakerMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Inline Transcript Section */}
              <AnimatePresence>
                {showTranscript && messages.length > 0 && (
                  <motion.div
                    className="transcript-section"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <div className="transcript-messages">
                      {messages.map((msg, idx) => (
                        <div key={idx} className={`message ${msg.role}`}>
                          <div className="message-content">{msg.text}</div>
                          <div className="message-time">
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {showTranscript && messages.length === 0 && (
                <div className="transcript-section">
                  <div className="transcript-empty">
                    <div className="transcript-empty-icon">
                      <MessageSquare size={24} />
                    </div>
                    <p>Your conversation will appear here</p>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Context Sidebar */}
            <div className="voice-card context-card">
              <div className="voice-card-header">
                <div className="voice-card-title">
                  <div className="voice-card-header-icon">
                    <User size={20} />
                  </div>
                  <h2>Personalization</h2>
                </div>
              </div>

              {/* Profile Status */}
              <div className={`profile-status ${hasPersonalization ? 'profile-status-complete' : 'profile-status-incomplete'}`}>
                <div className="profile-status-icon">
                  {hasPersonalization ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                </div>
                <div className="profile-status-text">
                  <strong>{hasPersonalization ? 'Personalized Mode' : 'Basic Mode'}</strong>
                  <span>{hasPersonalization ? 'Using your health data' : 'Add profile for better answers'}</span>
                </div>
              </div>

              {/* Context Section */}
              <div className="context-section">
                <div className="context-section-title">Health Context Used</div>

                {contextItems.length > 0 ? (
                  <div className="context-items">
                    {contextItems.map((item, idx) => (
                      <div key={idx} className="context-item">
                        <div className="context-item-icon">
                          <item.icon size={14} />
                        </div>
                        <div className="context-item-text">
                          <div className="context-item-label">{item.label}</div>
                          <div className="context-item-value">{item.value}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="context-empty">
                    No health data available yet. Complete your profile to see personalization context.
                  </div>
                )}
              </div>

              {contextSummary.reports_count !== undefined && contextSummary.reports_count > 0 && (
                <div className="context-section">
                  <div className="context-section-title">Reports Analyzed</div>
                  <div className="context-items">
                    <div className="context-item">
                      <div className="context-item-icon">
                        <Activity size={14} />
                      </div>
                      <div className="context-item-text">
                        <div className="context-item-label">Health Reports</div>
                        <div className="context-item-value">{contextSummary.reports_count} uploaded</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Error Toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="error-toast"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            onClick={() => setError(null)}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default VoiceAgent;
