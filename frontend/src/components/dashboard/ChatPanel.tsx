import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Maximize2, X, Bot } from 'lucide-react';
import { useAIAssistant } from '../../hooks/useDashboard';
import './ChatPanel.css';

interface ChatPanelProps {
  compact?: boolean;
}

function ChatPanel({ compact: _compact = false }: ChatPanelProps) {
  const { messages, isTyping, suggestions, sendMessage } = useAIAssistant();
  const [inputValue, setInputValue] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputValue]);

  const handleSend = () => {
    if (inputValue.trim()) {
      sendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const renderContent = () => (
    <>
      {/* Messages */}
      <div className="chat-messages-container dash-scrollbar">
        {messages.map((message) => (
          <motion.div
            key={message.id}
            className={`chat-message ${message.role}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className={`chat-message-avatar ${message.role}`}>
              {message.role === 'assistant' ? <Bot size={20} /> : 'U'}
            </div>
            <div>
              <div
                className="chat-message-content"
                dangerouslySetInnerHTML={{
                  __html: message.content
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br/>')
                    .replace(/• /g, '<br/>• '),
                }}
              />
              <div className={`chat-message-timestamp ${message.role === 'user' ? 'text-right' : ''}`}>
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </motion.div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <motion.div
            className="chat-typing-indicator"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="chat-message-avatar assistant">
              <Bot size={20} />
            </div>
            <div className="chat-typing-dots">
              <div className="chat-typing-dot" />
              <div className="chat-typing-dot" />
              <div className="chat-typing-dot" />
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions */}
      {suggestions.length > 0 && messages.length <= 2 && (
        <div className="chat-suggestions">
          <div className="chat-suggestions-label">Quick Questions</div>
          <div className="chat-suggestions-chips">
            {suggestions.map((suggestion, idx) => (
              <motion.button
                key={idx}
                className="chat-suggestion-chip"
                onClick={() => handleSuggestionClick(suggestion)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {suggestion}
              </motion.button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-input dash-focus-ring"
            placeholder="Ask me anything about your health..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <motion.button
            className="chat-send-button dash-btn dash-btn-primary dash-focus-ring"
            onClick={handleSend}
            disabled={!inputValue.trim() || isTyping}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Send size={20} />
          </motion.button>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Regular Card View */}
      <motion.div
        className="dash-card chat-panel-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <div className="dash-card-header chat-panel-header">
          <div className="chat-panel-title-group">
            <div className="chat-panel-title-icon">
              <Bot size={18} />
            </div>
            <h2 className="dash-card-title">AI Health Assistant</h2>
          </div>
          <motion.button
            className="dash-btn dash-btn-icon dash-focus-ring"
            onClick={() => setIsModalOpen(true)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Expand chat"
          >
            <Maximize2 size={18} />
          </motion.button>
        </div>

        <div className="chat-panel-body">
          {renderContent()}
        </div>
      </motion.div>

      {/* Modal View */}
      <AnimatePresence>
        {isModalOpen && (
          <motion.div
            className="chat-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsModalOpen(false)}
          >
            <motion.div
              className="chat-modal-content"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: 'spring', damping: 25 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="chat-modal-header">
                <h2 className="chat-modal-title">
                  <Bot size={28} />
                  AI Health Assistant
                </h2>
                <motion.button
                  className="dash-btn dash-btn-icon dash-focus-ring"
                  onClick={() => setIsModalOpen(false)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <X size={24} />
                </motion.button>
              </div>

              <div className="chat-modal-body">
                {renderContent()}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default ChatPanel;
