import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExternalLink, CheckCircle2, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';
import { cn } from '../utils/cn';

/**
 * SmartAnswer Component
 *
 * Displays the AI answer with:
 * - Rich typography
 * - Inline clickable citations [E1], [E2] as floating chips
 * - Confidence badge (Green/Yellow/Red)
 * - Expandable citation tooltips
 */
export const SmartAnswer = ({ answer, citations = [], evidence, metadata = {}, onCitationClick }) => {
  const [hoveredCitation, setHoveredCitation] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);

  // Build citation lookup map
  const citationMap = useMemo(() => {
    const map = {};
    citations.forEach(c => {
      map[c.evidence_id] = c;
    });
    // Also add evidence items
    if (evidence?.items) {
      evidence.items.forEach(item => {
        if (!map[item.id]) {
          map[item.id] = { evidence_id: item.id, url: item.url, title: item.title };
        } else {
          map[item.id] = { ...map[item.id], title: item.title, snippet: item.snippet };
        }
      });
    }
    return map;
  }, [citations, evidence]);

  // Parse answer and replace [E1], [E2] with interactive elements
  const parsedContent = useMemo(() => {
    if (!answer) return [];

    const parts = [];
    const regex = /\[E(\d+)\]/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(answer)) !== null) {
      // Add text before the citation
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: answer.slice(lastIndex, match.index)
        });
      }

      // Add citation
      const evidenceId = `E${match[1]}`;
      parts.push({
        type: 'citation',
        id: evidenceId,
        citation: citationMap[evidenceId]
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < answer.length) {
      parts.push({
        type: 'text',
        content: answer.slice(lastIndex)
      });
    }

    return parts;
  }, [answer, citationMap]);

  // Get confidence color and icon
  const getConfidenceStyle = (confidence) => {
    if (confidence >= 0.7) return { color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/50', icon: CheckCircle2 };
    if (confidence >= 0.4) return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/50', icon: AlertTriangle };
    return { color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/50', icon: XCircle };
  };

  // Get verdict style
  const getVerdictStyle = (verdict) => {
    switch (verdict) {
      case 'supported':
        return { color: 'text-green-400', label: 'Supported', icon: CheckCircle2 };
      case 'not_supported':
        return { color: 'text-red-400', label: 'Not Supported', icon: XCircle };
      case 'contested':
        return { color: 'text-yellow-400', label: 'Contested', icon: AlertTriangle };
      default:
        return { color: 'text-slate-400', label: 'Insufficient Evidence', icon: HelpCircle };
    }
  };

  const confidence = metadata?.confidence || 0;
  const confidenceStyle = getConfidenceStyle(confidence);
  const ConfidenceIcon = confidenceStyle.icon;

  const verdict = evidence?.overall_verdict;
  const verdictStyle = verdict ? getVerdictStyle(verdict) : null;
  const VerdictIcon = verdictStyle?.icon;

  return (
    <div className="space-y-4">
      {/* Confidence & Verdict Badges */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Confidence Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={cn(
            "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border",
            confidenceStyle.bg,
            confidenceStyle.border,
            confidenceStyle.color
          )}
        >
          <ConfidenceIcon className="w-4 h-4" />
          <span>{Math.round(confidence * 100)}% Confidence</span>
        </motion.div>

        {/* Verdict Badge */}
        {verdictStyle && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium",
              "bg-zinc-800 border border-zinc-700"
            )}
          >
            <VerdictIcon className={cn("w-4 h-4", verdictStyle.color)} />
            <span className={verdictStyle.color}>{verdictStyle.label}</span>
          </motion.div>
        )}

        {/* Source Count */}
        {citations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium bg-blue-500/20 border border-blue-500/50 text-blue-400"
          >
            <ExternalLink className="w-4 h-4" />
            <span>{citations.length} Sources</span>
          </motion.div>
        )}
      </div>

      {/* Answer with Inline Citations */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-lg leading-relaxed text-slate-200"
      >
        {parsedContent.map((part, idx) => {
          if (part.type === 'text') {
            return <span key={idx}>{part.content}</span>;
          }

          if (part.type === 'citation') {
            const isHovered = hoveredCitation === part.id;
            const isSelected = selectedCitation === part.id;

            return (
              <span key={idx} className="relative inline-block">
                <button
                  onClick={() => {
                    setSelectedCitation(isSelected ? null : part.id);
                    if (onCitationClick && !isSelected) {
                      onCitationClick(part.id);
                    }
                  }}
                  onMouseEnter={() => setHoveredCitation(part.id)}
                  onMouseLeave={() => setHoveredCitation(null)}
                  className={cn(
                    "inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-xs font-mono rounded transition-all",
                    "bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30",
                    isSelected && "ring-2 ring-cyan-500"
                  )}
                >
                  {part.id}
                </button>

                {/* Citation Tooltip */}
                <AnimatePresence>
                  {(isHovered || isSelected) && part.citation && (
                    <motion.div
                      initial={{ opacity: 0, y: 5, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 5, scale: 0.95 }}
                      className="absolute left-0 top-full mt-2 z-50 w-72 p-3 bg-slate-800 rounded-lg shadow-xl border border-slate-700"
                    >
                      <div className="space-y-2">
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-xs font-mono text-blue-400">{part.id}</span>
                          <a
                            href={part.citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                        {part.citation.title && (
                          <p className="text-sm font-medium text-slate-200 line-clamp-2">
                            {part.citation.title}
                          </p>
                        )}
                        {part.citation.snippet && (
                          <p className="text-xs text-slate-400 line-clamp-3">
                            {part.citation.snippet}
                          </p>
                        )}
                        <a
                          href={part.citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-slate-500 hover:text-slate-400 truncate"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {part.citation.url}
                        </a>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </span>
            );
          }

          return null;
        })}
      </motion.div>

      {/* Response Time */}
      {metadata?.latency_ms && (
        <p className="text-xs text-slate-500">
          Response time: {(metadata.latency_ms / 1000).toFixed(1)}s
          {metadata.is_mock && <span className="ml-2 text-yellow-500">Mock Mode</span>}
        </p>
      )}
    </div>
  );
};
