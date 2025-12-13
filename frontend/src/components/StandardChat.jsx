import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, AlertCircle, Sparkles } from 'lucide-react';
import { useCheckItAI } from '../hooks/useCheckItAI';
import { SmartAnswer } from './SmartAnswer';
import { EvidenceAccordion } from './EvidenceAccordion';
import { ProcessIndicator } from './ProcessIndicator';

/**
 * StandardChat Component
 *
 * Trust Engine interface with:
 * - Inline clickable citations
 * - Collapsible evidence accordion
 * - Process visibility (step indicator)
 * - Confidence badges
 */
export const StandardChat = () => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    messages,
    isLoading,
    sendQuery,
    clearMessages,
    getCurrentStep,
    getCompletedSteps,
  } = useCheckItAI();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    sendQuery(input);
    setInput('');
  };

  const handleExampleClick = (example) => {
    setInput(example);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Check-It AI</h1>
            <p className="text-sm text-slate-400">Trust Engine • Fact Verification</p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Clear Chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && !isLoading && (
            <WelcomeScreen onExampleClick={handleExampleClick} />
          )}

          <AnimatePresence mode="popLayout">
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <MessageBubble message={message} />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading State with Process Indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700"
            >
              <ProcessIndicator
                currentStep={getCurrentStep()}
                completedSteps={getCompletedSteps()}
                isComplete={false}
              />
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-800 p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex items-center gap-2 bg-slate-800 rounded-2xl p-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter a claim to verify..."
              disabled={isLoading}
              className="flex-1 bg-transparent px-4 py-3 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-xl p-3 transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-slate-500 text-center mt-2">
            Check-It AI can make mistakes. Verify important information.
          </p>
        </form>
      </div>
    </div>
  );
};

/**
 * WelcomeScreen Component
 */
const WelcomeScreen = ({ onExampleClick }) => {
  const examples = [
    { text: 'The Earth is flat', emoji: '🌍', trigger: 'mock:false' },
    { text: 'Vaccines are safe and effective', emoji: '💉', trigger: 'mock:true' },
    { text: 'Climate change is caused by humans', emoji: '🌡️', trigger: '' },
  ];

  return (
    <div className="mt-20">
      <div className="text-center mb-12">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="inline-block w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-4 mx-auto"
        >
          <Sparkles className="w-10 h-10" />
        </motion.div>
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-3xl font-bold mb-2"
        >
          Welcome to Check-It AI
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-slate-400 text-lg"
        >
          AI-powered fact verification with source citations
        </motion.p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {examples.map((example, idx) => (
          <motion.button
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + idx * 0.1 }}
            onClick={() => onExampleClick(example.trigger ? `${example.trigger} ${example.text}` : example.text)}
            className="p-4 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all hover:scale-105 text-left border border-slate-700 hover:border-slate-600"
          >
            <div className="text-2xl mb-2">{example.emoji}</div>
            <p className="text-sm text-slate-300">{example.text}</p>
          </motion.button>
        ))}
      </div>
    </div>
  );
};

/**
 * MessageBubble Component
 *
 * Renders user messages simply, but assistant messages use SmartAnswer + EvidenceAccordion
 */
const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.role === 'error';
  const isAssistant = message.role === 'assistant';

  // User Message
  if (isUser) {
    return (
      <div className="flex items-start gap-4 justify-end">
        <div className="bg-blue-600 rounded-2xl p-4 max-w-xl">
          <p className="text-slate-100">{message.content}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5" />
        </div>
      </div>
    );
  }

  // Error Message
  if (isError) {
    return (
      <div className="flex items-start gap-4">
        <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="bg-red-900/50 rounded-2xl p-4 border border-red-800">
          <p className="text-red-200">{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant Message with SmartAnswer + EvidenceAccordion
  if (isAssistant) {
    return (
      <div className="flex items-start gap-4">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5" />
        </div>
        <div className="flex-1 bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <SmartAnswer
            answer={message.content}
            citations={message.citations || []}
            evidence={message.evidence}
            metadata={message.metadata || {}}
          />

          {/* Evidence Accordion */}
          {message.evidence && (
            <EvidenceAccordion
              evidence={message.evidence}
              defaultExpanded={false}
            />
          )}
        </div>
      </div>
    );
  }

  return null;
};
