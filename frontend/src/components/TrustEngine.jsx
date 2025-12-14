import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronRight, Flame, CheckCircle2, XCircle, AlertTriangle, Globe, ExternalLink, X, History, Clock, GitFork, BookOpen, Scale, PenTool } from 'lucide-react';
import { useCheckItAI } from '../hooks/useCheckItAI';

/**
 * TrustEngine Component - "Void Aesthetic"
 *
 * Cinematic, immersive design where the answer is the hero.
 * Pure black background with glassmorphism cards and neon glows.
 */
export const TrustEngine = () => {
  const [input, setInput] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [showDrawer, setShowDrawer] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedHistoryIndex, setSelectedHistoryIndex] = useState(null);
  const [selectedClaimIndex, setSelectedClaimIndex] = useState(null); // For multi-claim view
  const inputRef = useRef(null);

  const {
    messages,
    isLoading,
    sendQuery,
    clearMessages,
    getCurrentStep,
    getCompletedSteps,
  } = useCheckItAI();

  // Get history pairs (user query + assistant response)
  const historyPairs = useMemo(() => {
    const pairs = [];
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === 'user' && messages[i + 1]?.role === 'assistant') {
        pairs.push({
          query: messages[i],
          response: messages[i + 1],
          index: pairs.length,
        });
      }
    }
    return pairs;
  }, [messages]);

  // Current display - either selected history item or latest
  const currentPair = selectedHistoryIndex !== null
    ? historyPairs[selectedHistoryIndex]
    : historyPairs[historyPairs.length - 1];

  const latestResponse = currentPair?.response;
  const latestQuery = currentPair?.query;

  useEffect(() => {
    if (!hasSearched) inputRef.current?.focus();
  }, [hasSearched]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    setHasSearched(true);
    setShowDrawer(false);
    setShowHistory(false);
    setSelectedHistoryIndex(null); // Show latest result
    setSelectedClaimIndex(null); // Reset claim selection for new query
    sendQuery(input);
    setInput('');
  };

  const handleReset = () => {
    setHasSearched(false);
    setShowDrawer(false);
    setSelectedClaimIndex(null);
    clearMessages();
    setInput('');
  };

  return (
    <div className="min-h-screen text-white overflow-hidden relative bg-[#050505]">
      {/* The Void - Mesh gradient background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(30, 58, 138, 0.08) 0%, #050505 50%, #050505 100%)'
        }}
      />

      {/* Minimal Header - Only when searched */}
      <AnimatePresence>
        {hasSearched && (
          <motion.header
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed top-0 left-0 right-0 z-50"
          >
            <div className="px-8 py-5 flex items-center justify-between">
              <button onClick={handleReset} className="flex items-center gap-2.5 opacity-60 hover:opacity-100 transition-opacity">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <Flame className="w-4 h-4" />
                </div>
                <span className="font-semibold text-sm tracking-wide">
                  <span className="text-amber-500">CheckIt</span>
                  <span className="text-white/60">-AI</span>
                </span>
              </button>

              {/* Minimal search in header */}
              <form onSubmit={handleSubmit} className="flex-1 max-w-md mx-8">
                <div className="flex items-center bg-white/[0.03] backdrop-blur-sm rounded-full border border-white/10 px-4 py-2">
                  <Search className="w-4 h-4 text-white/30" />
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Verify another claim..."
                    disabled={isLoading}
                    className="flex-1 bg-transparent px-3 py-1 text-sm focus:outline-none placeholder:text-white/20 text-white/80"
                  />
                </div>
              </form>

              {/* History Button - always render container for consistent layout */}
              <div className="w-16 flex justify-end">
                {historyPairs.length > 0 && (
                  <button
                    onClick={() => setShowHistory(!showHistory)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${
                      showHistory ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/5'
                    }`}
                  >
                    <History className="w-4 h-4" />
                    <span className="text-sm">{historyPairs.length}</span>
                  </button>
                )}
              </div>
            </div>
          </motion.header>
        )}
      </AnimatePresence>

      {/* History Panel */}
      <AnimatePresence>
        {showHistory && hasSearched && (
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed left-0 top-20 w-80 h-[calc(100vh-80px)] z-40"
          >
            <HistoryPanel
              historyPairs={historyPairs}
              selectedIndex={selectedHistoryIndex}
              onSelect={(index) => {
                setSelectedHistoryIndex(index);
                setSelectedClaimIndex(null); // Reset claim selection when switching history
                setShowHistory(false);
                setShowDrawer(false);
              }}
              onClose={() => setShowHistory(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <AnimatePresence mode="wait">
        {/* Hero State - Centered Search */}
        {!hasSearched && (
          <motion.div
            key="hero"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="min-h-screen flex flex-col items-center justify-center px-4"
          >
            {/* Logo */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', damping: 20 }}
              className="mb-12 flex items-center gap-4"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-2xl shadow-amber-500/30">
                <Flame className="w-9 h-9" />
              </div>
              <h1 className="text-5xl font-bold tracking-tight">
                <span className="text-amber-500">CheckIt</span>
                <span className="text-white">-AI</span>
              </h1>
            </motion.div>

            {/* Search Bar */}
            <motion.form
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              onSubmit={handleSubmit}
              className="w-full max-w-2xl"
            >
              <div className="relative group">
                {/* Glow effect */}
                <div className="absolute -inset-1 bg-gradient-to-r from-amber-500/30 via-orange-500/20 to-cyan-500/30 rounded-2xl blur-xl opacity-50 group-hover:opacity-80 transition-opacity duration-500" />

                <div className="relative flex items-center bg-white/[0.03] backdrop-blur-xl rounded-2xl border border-white/10 group-hover:border-white/20 transition-colors">
                  <div className="pl-6">
                    <Search className="w-5 h-5 text-white/40" />
                  </div>
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Enter a claim to verify..."
                    className="flex-1 bg-transparent px-4 py-5 text-lg focus:outline-none placeholder:text-white/30 text-white"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim()}
                    className="m-2 px-8 py-3.5 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 disabled:from-white/5 disabled:to-white/5 disabled:text-white/30 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-amber-500/20 disabled:shadow-none"
                  >
                    Verify
                  </button>
                </div>
              </div>
            </motion.form>

            {/* Example Claims */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-10 flex flex-wrap justify-center gap-3"
            >
              {['The Great Wall is visible from space', 'Napoleon was short', 'Vikings wore horned helmets'].map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setInput(ex)}
                  className="px-4 py-2 text-sm text-white/50 hover:text-white/80 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 rounded-full transition-all"
                >
                  {ex}
                </button>
              ))}
            </motion.div>
          </motion.div>
        )}

        {/* Results State */}
        {hasSearched && (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="min-h-screen flex items-center justify-center"
          >
            {/* Loading - Workflow Visualization */}
            {isLoading && (
              <div className="flex flex-col items-center">
                <WorkflowVisualization currentStep={getCurrentStep()} completedSteps={getCompletedSteps()} />
              </div>
            )}

            {/* Results - Multi-claim Cards or Single Card */}
            {latestResponse && !isLoading && (
              <div className={`w-full flex items-start pt-20 pb-10 transition-all duration-500 ease-out ${showDrawer ? 'pr-[45%]' : ''}`}>
                <div className={`transition-all duration-500 ease-out mx-auto ${showDrawer ? 'max-w-2xl px-8' : 'max-w-3xl px-8'}`}>
                  {/* Check if we have multiple findings (multi-claim query) */}
                  {latestResponse.evidence?.findings?.length > 1 ? (
                    <div className="space-y-6">
                      {/* Overall summary header */}
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center mb-4"
                      >
                        <h2 className="text-2xl font-bold text-white/90 mb-2">{latestQuery?.content}</h2>
                        <p className="text-sm text-white/50">{latestResponse.evidence.findings.length} claims analyzed</p>
                      </motion.div>

                      {/* Individual claim cards */}
                      {latestResponse.evidence.findings.map((finding, idx) => (
                        <ClaimCard
                          key={idx}
                          claim={finding.claim}
                          verdict={finding.verdict}
                          evidenceIds={finding.evidence_ids}
                          evidenceItems={latestResponse.evidence.items}
                          onSelect={() => {
                            // If clicking the same card that's already selected, toggle drawer
                            if (selectedClaimIndex === idx) {
                              setShowDrawer(!showDrawer);
                            } else {
                              // Select new claim and open drawer
                              setSelectedClaimIndex(idx);
                              setShowDrawer(true);
                            }
                          }}
                          isSelected={selectedClaimIndex === idx}
                          showDrawer={showDrawer}
                          index={idx}
                        />
                      ))}
                    </div>
                  ) : (
                    <VoidCard
                      query={latestQuery?.content}
                      response={latestResponse}
                      onToggleDrawer={() => setShowDrawer(!showDrawer)}
                      evidenceCount={latestResponse.evidence?.items?.length || 0}
                      showDrawer={showDrawer}
                    />
                  )}
                </div>

                {/* Evidence Drawer */}
                <AnimatePresence>
                  {showDrawer && latestResponse.evidence && (
                    <motion.div
                      initial={{ opacity: 0, x: 50 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 50 }}
                      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                      className="w-[45%] h-[calc(100vh-80px)] fixed right-0 top-20"
                    >
                      <EvidencePanel
                        evidence={latestResponse.evidence}
                        onClose={() => setShowDrawer(false)}
                        // For multi-claim: filter by selected claim's evidence
                        filteredEvidenceIds={
                          latestResponse.evidence?.findings?.length > 1 && selectedClaimIndex !== null
                            ? latestResponse.evidence.findings[selectedClaimIndex]?.evidence_ids
                            : null
                        }
                        claimText={
                          latestResponse.evidence?.findings?.length > 1 && selectedClaimIndex !== null
                            ? latestResponse.evidence.findings[selectedClaimIndex]?.claim
                            : null
                        }
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/**
 * Workflow Visualization - Minimal loading state
 */
const WorkflowVisualization = ({ currentStep, completedSteps }) => {
  const steps = [
    { id: 'router', label: 'Routing', Icon: GitFork },
    { id: 'researcher', label: 'Researching', Icon: BookOpen },
    { id: 'analyst', label: 'Analyzing', Icon: Scale },
    { id: 'writer', label: 'Writing', Icon: PenTool },
  ];

  return (
    <div className="flex flex-col items-center gap-8">
      <div className="flex items-center gap-6">
        {steps.map((step, i) => {
          const status = completedSteps.includes(step.id) ? 'done' : currentStep === step.id ? 'active' : 'pending';
          const StepIcon = step.Icon;
          return (
            <div key={step.id} className="flex items-center gap-6">
              <motion.div
                className="flex flex-col items-center gap-3"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                  status === 'done'
                    ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                    : status === 'active'
                    ? 'bg-white/5 border border-white/20 text-white animate-pulse'
                    : 'bg-white/[0.02] border border-white/5 text-white/30'
                }`}>
                  {status === 'done' ? <CheckCircle2 className="w-6 h-6" /> : <StepIcon className="w-6 h-6" />}
                </div>
                <span className={`text-xs font-medium ${
                  status === 'done' ? 'text-green-400/80' : status === 'active' ? 'text-white/80' : 'text-white/30'
                }`}>
                  {step.label}
                </span>
              </motion.div>
              {i < steps.length - 1 && (
                <div className={`w-12 h-px ${status === 'done' ? 'bg-green-500/30' : 'bg-white/10'}`} />
              )}
            </div>
          );
        })}
      </div>

      {currentStep && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-white/40 text-sm"
        >
          {currentStep === 'router' && 'Analyzing your query...'}
          {currentStep === 'researcher' && 'Searching trusted sources...'}
          {currentStep === 'analyst' && 'Evaluating evidence...'}
          {currentStep === 'writer' && 'Composing response...'}
        </motion.p>
      )}
    </div>
  );
};

/**
 * VoidCard - The Hero Truth Card with Glassmorphism
 */
const VoidCard = ({ query, response, onToggleDrawer, evidenceCount, showDrawer }) => {
  const confidence = response.metadata?.confidence || 0;
  const verdict = response.evidence?.overall_verdict;
  const route = response.route || response.metadata?.route;

  // Verdict styling with neon glows - check route first for out_of_scope
  const verdictInfo = route === 'out_of_scope'
    ? {
        label: 'OUT OF SCOPE',
        color: 'text-purple-400',
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/20',
        glow: 'shadow-[0_0_20px_-5px_rgba(168,85,247,0.3)]',
        Icon: AlertTriangle
      }
    : verdict === 'supported'
    ? {
        label: 'VERIFIED TRUE',
        color: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        glow: 'shadow-[0_0_20px_-5px_rgba(74,222,128,0.3)]',
        Icon: CheckCircle2
      }
    : verdict === 'not_supported'
    ? {
        label: 'VERIFIED FALSE',
        color: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        glow: 'shadow-[0_0_20px_-5px_rgba(248,113,113,0.3)]',
        Icon: XCircle
      }
    : {
        label: 'UNCERTAIN',
        color: 'text-yellow-400',
        bg: 'bg-yellow-500/10',
        border: 'border-yellow-500/20',
        glow: 'shadow-[0_0_20px_-5px_rgba(250,204,21,0.3)]',
        Icon: AlertTriangle
      };

  // Parse citations into styled chips
  const parsedContent = useMemo(() => {
    const text = response.content || '';
    const parts = [];
    const regex = /\[E(\d+)\]/g;
    let lastIdx = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIdx) {
        parts.push({ type: 'text', content: text.slice(lastIdx, match.index) });
      }
      parts.push({ type: 'citation', id: `E${match[1]}` });
      lastIdx = match.index + match[0].length;
    }
    if (lastIdx < text.length) {
      parts.push({ type: 'text', content: text.slice(lastIdx) });
    }
    return parts;
  }, [response.content]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', damping: 25 }}
      className="relative"
    >
      {/* Card glow */}
      <div className="absolute -inset-px bg-gradient-to-b from-white/10 to-transparent rounded-3xl opacity-50" />

      {/* The Card */}
      <div className="relative bg-white/[0.02] backdrop-blur-2xl rounded-3xl border border-white/10 p-10 shadow-[0_0_80px_-20px_rgba(0,0,0,0.5)]">

        {/* Verdict Badge - Neon Glow */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className={`inline-flex items-center gap-2 px-5 py-2 rounded-full text-sm font-bold border ${verdictInfo.bg} ${verdictInfo.color} ${verdictInfo.border} ${verdictInfo.glow} mb-8`}
        >
          <verdictInfo.Icon className="w-4 h-4" />
          {verdictInfo.label}
        </motion.div>

        {/* The Answer - Hero Typography */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight text-white/90 mb-6 leading-tight">
            {query}
          </h2>

          <div className="text-lg leading-relaxed text-zinc-300/80">
            {parsedContent.map((part, i) =>
              part.type === 'text' ? (
                <span key={i}>{part.content}</span>
              ) : (
                <CitationChip key={i} id={part.id} onClick={onToggleDrawer} />
              )
            )}
          </div>
        </div>

        {/* Footer - Confidence + Evidence Toggle */}
        <div className="flex items-center justify-between pt-6 border-t border-white/5">
          {/* Confidence Badge with Glow */}
          <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium border ${
            confidence >= 0.7
              ? 'bg-green-500/10 text-green-400 border-green-500/20 shadow-[0_0_15px_-3px_rgba(74,222,128,0.2)]'
              : confidence >= 0.4
              ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20 shadow-[0_0_15px_-3px_rgba(250,204,21,0.2)]'
              : 'bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_15px_-3px_rgba(248,113,113,0.2)]'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              confidence >= 0.7 ? 'bg-green-400' : confidence >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'
            }`} />
            {Math.round(confidence * 100)}% Confidence
          </div>

          {/* Evidence Toggle */}
          {evidenceCount > 0 && (
            <motion.button
              onClick={onToggleDrawer}
              whileHover={{ x: 3 }}
              className={`flex items-center gap-2 text-sm transition-colors ${
                showDrawer ? 'text-white/80' : 'text-white/40 hover:text-white/70'
              }`}
            >
              {evidenceCount} sources
              <ChevronRight className={`w-4 h-4 transition-transform ${showDrawer ? 'rotate-180' : ''}`} />
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
};

/**
 * ClaimCard - Individual claim card for multi-claim queries
 * Selectable card that shows evidence in the panel when clicked
 */
const ClaimCard = ({ claim, verdict, evidenceIds, evidenceItems, onSelect, isSelected, showDrawer, index }) => {
  // Get relevant evidence items for this claim
  const relevantEvidence = useMemo(() => {
    if (!evidenceItems || !evidenceIds) return [];
    return evidenceItems.filter(item => evidenceIds.includes(item.id));
  }, [evidenceItems, evidenceIds]);

  // Verdict styling and explanation
  const verdictInfo = verdict === 'supported'
    ? {
        label: 'TRUE',
        color: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/20',
        glow: 'shadow-[0_0_15px_-5px_rgba(74,222,128,0.3)]',
        Icon: CheckCircle2,
        explanation: 'Evidence confirms this claim is accurate.'
      }
    : verdict === 'not_supported'
    ? {
        label: 'FALSE',
        color: 'text-red-400',
        bg: 'bg-red-500/10',
        border: 'border-red-500/20',
        glow: 'shadow-[0_0_15px_-5px_rgba(248,113,113,0.3)]',
        Icon: XCircle,
        explanation: 'Evidence contradicts this claim.'
      }
    : verdict === 'contested'
    ? {
        label: 'CONTESTED',
        color: 'text-orange-400',
        bg: 'bg-orange-500/10',
        border: 'border-orange-500/20',
        glow: 'shadow-[0_0_15px_-5px_rgba(251,146,60,0.3)]',
        Icon: AlertTriangle,
        explanation: 'Sources provide conflicting information on this claim.'
      }
    : {
        label: 'INSUFFICIENT',
        color: 'text-yellow-400',
        bg: 'bg-yellow-500/10',
        border: 'border-yellow-500/20',
        glow: 'shadow-[0_0_15px_-5px_rgba(250,204,21,0.3)]',
        Icon: AlertTriangle,
        explanation: 'Not enough evidence to verify this claim.'
      };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, type: 'spring', damping: 25 }}
      className="relative cursor-pointer"
      onClick={onSelect}
    >
      {/* Card glow - stronger when selected */}
      <div className={`absolute -inset-px bg-gradient-to-b rounded-2xl transition-opacity duration-300 ${
        isSelected
          ? 'from-white/20 to-white/5 opacity-100'
          : 'from-white/5 to-transparent opacity-50'
      }`} />

      {/* The Card */}
      <div className={`relative bg-white/[0.02] backdrop-blur-xl rounded-2xl border p-6 transition-all duration-300 ${
        isSelected
          ? 'border-white/30 shadow-[0_0_30px_-10px_rgba(255,255,255,0.15)]'
          : 'border-white/10 hover:border-white/20'
      }`}>
        {/* Header: Verdict Badge */}
        <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border ${verdictInfo.bg} ${verdictInfo.color} ${verdictInfo.border} ${verdictInfo.glow} mb-4`}>
          <verdictInfo.Icon className="w-3.5 h-3.5" />
          {verdictInfo.label}
        </div>

        {/* Claim text */}
        <h3 className="text-lg text-white/90 font-medium mb-3">{claim}</h3>

        {/* Verdict explanation */}
        <p className="text-sm text-white/60 mb-4">{verdictInfo.explanation}</p>

        {/* Evidence snippets for this claim - only show when NOT selected (collapsed view) */}
        {!isSelected && relevantEvidence.length > 0 && (
          <div className="space-y-2 pt-3 border-t border-white/5">
            {relevantEvidence.slice(0, 2).map((item) => (
              <div key={item.id} className="flex items-start gap-2">
                <span className="text-xs font-mono text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded flex-shrink-0">
                  {item.id}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white/60 line-clamp-1">
                    {item.snippet || item.title}
                  </p>
                </div>
              </div>
            ))}
            {relevantEvidence.length > 2 && (
              <p className="text-xs text-white/30 pl-8">+{relevantEvidence.length - 2} more sources</p>
            )}
          </div>
        )}

        {/* Footer - show source count and expand indicator */}
        <div className="flex items-center justify-between pt-3 border-t border-white/5 mt-3">
          <span className="text-xs text-white/40">
            {evidenceIds.length} source{evidenceIds.length !== 1 ? 's' : ''}
          </span>
          <div className={`flex items-center gap-1 text-xs transition-colors ${
            isSelected ? 'text-white/70' : 'text-white/40'
          }`}>
            {isSelected && showDrawer ? 'Viewing evidence' : 'Click to view evidence'}
            <ChevronRight className={`w-3 h-3 transition-transform ${isSelected && showDrawer ? 'rotate-180' : ''}`} />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

/**
 * CitationChip - Inline citation with glow effect
 */
const CitationChip = ({ id, onClick }) => (
  <motion.button
    onClick={onClick}
    initial={{ opacity: 0, scale: 0.8 }}
    animate={{ opacity: 1, scale: 1 }}
    whileHover={{ scale: 1.05 }}
    className="inline-flex items-center px-2 py-0.5 mx-1 rounded-md text-xs font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30 cursor-pointer hover:bg-blue-500/30 hover:border-blue-500/40 transition-all shadow-[0_0_10px_-3px_rgba(59,130,246,0.3)]"
  >
    {id}
  </motion.button>
);

/**
 * EvidencePanel - Slide-in panel with source cards
 * Can show all evidence or filtered by claim
 */
const EvidencePanel = ({ evidence, onClose, filteredEvidenceIds = null, claimText = null }) => {
  // If filteredEvidenceIds is provided, only show those items
  const allItems = evidence.items || [];
  const items = filteredEvidenceIds
    ? allItems.filter(item => filteredEvidenceIds.includes(item.id))
    : allItems;

  return (
    <div className="h-full bg-[#080808] border-l border-white/5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/5">
        <div>
          <h3 className="font-semibold text-white/90">Evidence</h3>
          {claimText ? (
            <p className="text-xs text-white/40 mt-0.5 line-clamp-1 max-w-[250px]">
              For: "{claimText}"
            </p>
          ) : (
            <p className="text-xs text-white/40 mt-0.5">{items.length} sources analyzed</p>
          )}
        </div>
        <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
          <X className="w-4 h-4 text-white/40" />
        </button>
      </div>

      {/* Source count badge if filtered */}
      {filteredEvidenceIds && (
        <div className="px-6 py-2 bg-white/[0.02] border-b border-white/5">
          <span className="text-xs text-white/50">
            {items.length} of {allItems.length} sources for this claim
          </span>
        </div>
      )}

      {/* Source List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {items.length > 0 ? (
          items.map((item, idx) => (
            <SourceCard key={item.id || idx} item={item} index={idx} />
          ))
        ) : (
          <div className="text-center py-8 text-white/30 text-sm">
            No evidence found for this claim
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * HistoryPanel - Side panel showing past queries and verdicts
 */
const HistoryPanel = ({ historyPairs, selectedIndex, onSelect, onClose }) => {
  const getVerdictInfo = (response) => {
    const route = response.route || response.metadata?.route;
    const verdict = response.evidence?.overall_verdict;

    if (route === 'out_of_scope') {
      return { label: 'OUT OF SCOPE', color: 'text-purple-400', bg: 'bg-purple-500/20', Icon: AlertTriangle };
    }
    if (verdict === 'supported') {
      return { label: 'TRUE', color: 'text-green-400', bg: 'bg-green-500/20', Icon: CheckCircle2 };
    }
    if (verdict === 'not_supported') {
      return { label: 'FALSE', color: 'text-red-400', bg: 'bg-red-500/20', Icon: XCircle };
    }
    return { label: 'UNCERTAIN', color: 'text-yellow-400', bg: 'bg-yellow-500/20', Icon: AlertTriangle };
  };

  return (
    <div className="h-full bg-[#080808] border-r border-white/5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-white/50" />
          <h3 className="font-semibold text-white/90 text-sm">History</h3>
        </div>
        <button onClick={onClose} className="p-1.5 hover:bg-white/5 rounded-lg transition-colors">
          <X className="w-4 h-4 text-white/40" />
        </button>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {historyPairs.slice().reverse().map((pair, idx) => {
          const actualIndex = historyPairs.length - 1 - idx;
          const isSelected = selectedIndex === actualIndex;
          const verdictInfo = getVerdictInfo(pair.response);

          return (
            <motion.button
              key={pair.query.id}
              onClick={() => onSelect(actualIndex)}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.03 }}
              className={`w-full text-left p-3 rounded-xl transition-all ${
                isSelected
                  ? 'bg-white/10 border border-white/20'
                  : 'bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/10'
              }`}
            >
              {/* Query text */}
              <p className="text-sm text-white/80 line-clamp-2 mb-2">
                {pair.query.content}
              </p>

              {/* Verdict badge */}
              <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${verdictInfo.bg} ${verdictInfo.color}`}>
                <verdictInfo.Icon className="w-3 h-3" />
                {verdictInfo.label}
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
};

/**
 * SourceCard - Individual evidence source
 */
const SourceCard = ({ item, index }) => {
  const getFavicon = (url) => {
    try { return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=32`; }
    catch { return null; }
  };

  const getDomain = (d) => d?.replace('www.', '') || 'source';

  return (
    <motion.a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="block p-4 bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 hover:border-white/10 rounded-xl transition-all group"
    >
      <div className="flex items-start gap-3">
        {/* Favicon */}
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0 overflow-hidden">
          {getFavicon(item.url) ? (
            <img src={getFavicon(item.url)} alt="" className="w-4 h-4" onError={(e) => e.target.style.display='none'} />
          ) : (
            <Globe className="w-4 h-4 text-white/30" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* ID + Domain */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-blue-400">{item.id}</span>
            <span className="text-xs text-white/30">{getDomain(item.display_domain)}</span>
          </div>

          {/* Title */}
          <h4 className="text-sm text-white/80 font-medium line-clamp-2 group-hover:text-white transition-colors">
            {item.title || 'Source'}
          </h4>

          {/* Snippet */}
          {item.snippet && (
            <p className="text-xs text-white/40 mt-1.5 line-clamp-2">{item.snippet}</p>
          )}
        </div>

        <ExternalLink className="w-4 h-4 text-white/20 group-hover:text-white/50 flex-shrink-0 transition-colors" />
      </div>
    </motion.a>
  );
};

export default TrustEngine;
