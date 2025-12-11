import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, AlertCircle, ExternalLink, FileText, ChevronRight, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useCheckItAI } from '../hooks/useCheckItAI';
import { cn } from '../utils/cn';

/**
 * StandardChat Component
 *
 * ChatGPT-style interface with:
 * - Message bubbles
 * - Evidence panel (sidebar)
 * - Input area
 * - Loading states
 */
export const StandardChat = () => {
  const [input, setInput] = useState('');
  const [showEvidence, setShowEvidence] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    messages,
    isLoading,
    currentEvidence,
    sendQuery,
    clearMessages,
    getLoadingMessage,
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
    <div className="flex h-screen bg-slate-900 text-slate-100">
      {/* Main Chat Area */}
      <div className={cn(
        "flex flex-col transition-all duration-300",
        showEvidence ? "w-2/3" : "w-full"
      )}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Check-It AI</h1>
              <p className="text-sm text-slate-400">Fact Verification Assistant</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={clearMessages}
                className="px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Clear Chat
              </button>
            )}
            {currentEvidence && (
              <button
                onClick={() => setShowEvidence(!showEvidence)}
                className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                {showEvidence ? 'Hide' : 'Show'} Evidence
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.length === 0 && !isLoading && (
            <div className="max-w-3xl mx-auto mt-20">
              <div className="text-center mb-12">
                <div className="inline-block w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-4">
                  <Bot className="w-12 h-12" />
                </div>
                <h2 className="text-3xl font-bold mb-2">Welcome to Check-It AI</h2>
                <p className="text-slate-400 text-lg">
                  Your AI-powered fact verification assistant
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { text: 'The Earth is round', emoji: '🌍' },
                  { text: 'Vaccines cause autism', emoji: '💉' },
                  { text: 'Climate change is real', emoji: '🌡️' },
                ].map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleClick(example.text)}
                    className="p-4 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all hover:scale-105 text-left"
                  >
                    <div className="text-2xl mb-2">{example.emoji}</div>
                    <p className="text-sm text-slate-300">{example.text}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="flex items-start gap-4 max-w-3xl mx-auto">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div className="flex-1 bg-slate-800 rounded-2xl p-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                  <span className="text-slate-300">{getLoadingMessage()}</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
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

      {/* Evidence Sidebar */}
      {showEvidence && currentEvidence && (
        <div className="w-1/3 border-l border-slate-800 overflow-y-auto">
          <EvidencePanel evidence={currentEvidence} />
        </div>
      )}
    </div>
  );
};

/**
 * MessageBubble Component
 */
const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.role === 'error';

  return (
    <div className={cn(
      "flex items-start gap-4 max-w-3xl",
      isUser ? "ml-auto flex-row-reverse" : "mx-auto"
    )}>
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
        isUser ? "bg-slate-700" : isError ? "bg-red-600" : "bg-gradient-to-br from-blue-500 to-purple-600"
      )}>
        {isUser ? <User className="w-5 h-5" /> :
         isError ? <AlertCircle className="w-5 h-5" /> :
         <Bot className="w-5 h-5" />}
      </div>

      {/* Content */}
      <div className={cn(
        "flex-1 rounded-2xl p-4",
        isUser ? "bg-blue-600" : isError ? "bg-red-900/50" : "bg-slate-800"
      )}>
        {isUser ? (
          <p className="text-slate-100">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-700">
                <p className="text-xs text-slate-400 mb-2 font-semibold">Sources:</p>
                <div className="space-y-2">
                  {message.citations.map((citation, idx) => (
                    <a
                      key={idx}
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span>{citation.evidence_id}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-400 truncate">{citation.url}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            {message.metadata && (
              <div className="mt-4 pt-4 border-t border-slate-700 flex items-center gap-4 text-xs text-slate-500">
                {message.metadata.confidence && (
                  <span>Confidence: {(message.metadata.confidence * 100).toFixed(0)}%</span>
                )}
                {message.metadata.latency_ms && (
                  <span>Response time: {message.metadata.latency_ms}ms</span>
                )}
                {message.metadata.is_mock && (
                  <span className="text-yellow-500">⚠️ Mock Mode</span>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/**
 * EvidencePanel Component
 */
const EvidencePanel = ({ evidence }) => {
  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
        <FileText className="w-5 h-5" />
        Evidence Bundle
      </h2>

      {/* Overall Verdict */}
      <div className="mb-6 p-4 bg-slate-800 rounded-lg">
        <p className="text-sm text-slate-400 mb-1">Overall Verdict</p>
        <p className={cn(
          "text-lg font-semibold capitalize",
          evidence.overall_verdict === 'supported' ? 'text-green-400' :
          evidence.overall_verdict === 'not_supported' ? 'text-red-400' :
          'text-yellow-400'
        )}>
          {evidence.overall_verdict.replace('_', ' ')}
        </p>
      </div>

      {/* Evidence Items */}
      {evidence.items && evidence.items.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">
            Sources ({evidence.items.length})
          </h3>
          {evidence.items.map((item, idx) => (
            <div key={idx} className="p-4 bg-slate-800 rounded-lg space-y-2">
              <div className="flex items-start justify-between">
                <span className="text-xs font-mono text-blue-400">{item.id}</span>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-slate-400 line-clamp-3">{item.snippet}</p>
              <p className="text-xs text-slate-500">{item.display_domain}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
