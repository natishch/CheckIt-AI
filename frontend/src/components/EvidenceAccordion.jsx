import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ExternalLink, Shield, ShieldCheck, ShieldAlert, Globe } from 'lucide-react';
import { cn } from '../utils/cn';

/**
 * EvidenceAccordion Component
 *
 * Collapsible evidence drawer with:
 * - "Peeking" preview state showing source count
 * - Expandable accordion for each source
 * - Domain favicon and credibility indicators
 * - Card layout with title, snippet, and credibility score
 */
export const EvidenceAccordion = ({ evidence, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [expandedItems, setExpandedItems] = useState({});

  const items = evidence?.items || [];
  const findings = evidence?.findings || [];

  // Domain credibility scoring
  const getCredibilityInfo = (domain) => {
    const highCredibility = ['.gov', '.edu', 'wikipedia.org', 'britannica.com', 'nationalgeographic.com'];
    const mediumCredibility = ['reuters.com', 'apnews.com', 'bbc.com', 'nytimes.com', 'history.com', 'smithsonianmag.com'];

    const domainLower = domain?.toLowerCase() || '';

    if (highCredibility.some(d => domainLower.includes(d))) {
      return { level: 'high', label: 'High Credibility', color: 'text-green-400', bgColor: 'bg-green-500/20', icon: ShieldCheck };
    }
    if (mediumCredibility.some(d => domainLower.includes(d))) {
      return { level: 'medium', label: 'Trusted Source', color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: Shield };
    }
    return { level: 'standard', label: 'Web Source', color: 'text-slate-400', bgColor: 'bg-slate-500/20', icon: Globe };
  };

  // Get favicon URL
  const getFaviconUrl = (url) => {
    try {
      const domain = new URL(url).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
      return null;
    }
  };

  const toggleItem = (id) => {
    setExpandedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      {/* Accordion Header - Always Visible */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "w-full flex items-center justify-between p-4 rounded-xl transition-all",
          "bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50",
          isExpanded && "rounded-b-none border-b-0"
        )}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-left">
            <p className="font-medium text-slate-200">
              {items.length} Sources Verified
            </p>
            <p className="text-sm text-slate-400">
              {findings.length > 0 ? `${findings.length} claims analyzed` : 'Click to view evidence'}
            </p>
          </div>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-5 h-5 text-slate-400" />
        </motion.div>
      </motion.button>

      {/* Accordion Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="p-4 bg-slate-800/30 border border-t-0 border-slate-700/50 rounded-b-xl space-y-3">
              {/* Findings Summary */}
              {findings.length > 0 && (
                <div className="mb-4 p-3 bg-slate-900/50 rounded-lg">
                  <p className="text-xs uppercase tracking-wide text-slate-500 mb-2">Key Findings</p>
                  <div className="space-y-2">
                    {findings.map((finding, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs font-medium",
                          finding.verdict === 'supported' ? 'bg-green-500/20 text-green-400' :
                          finding.verdict === 'not_supported' ? 'bg-red-500/20 text-red-400' :
                          'bg-yellow-500/20 text-yellow-400'
                        )}>
                          {finding.verdict.replace('_', ' ')}
                        </span>
                        <span className="text-slate-300 flex-1">{finding.claim}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Cards */}
              {items.map((item, idx) => {
                const credibility = getCredibilityInfo(item.display_domain);
                const CredIcon = credibility.icon;
                const isItemExpanded = expandedItems[item.id];
                const faviconUrl = getFaviconUrl(item.url);

                return (
                  <motion.div
                    key={item.id || idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="bg-slate-900/50 rounded-lg overflow-hidden border border-slate-700/30"
                  >
                    {/* Card Header */}
                    <button
                      onClick={() => toggleItem(item.id)}
                      className="w-full p-3 flex items-start gap-3 text-left hover:bg-slate-800/50 transition-colors"
                    >
                      {/* Favicon */}
                      <div className="w-8 h-8 rounded bg-slate-700 flex items-center justify-center flex-shrink-0 overflow-hidden">
                        {faviconUrl ? (
                          <img src={faviconUrl} alt="" className="w-5 h-5" onError={(e) => e.target.style.display = 'none'} />
                        ) : (
                          <Globe className="w-4 h-4 text-slate-400" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-blue-400">{item.id}</span>
                          <span className={cn(
                            "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs",
                            credibility.bgColor, credibility.color
                          )}>
                            <CredIcon className="w-3 h-3" />
                            {credibility.label}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-slate-200 line-clamp-1">
                          {item.title || 'Untitled Source'}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {item.display_domain}
                        </p>
                      </div>

                      {/* Expand Icon */}
                      <motion.div
                        animate={{ rotate: isItemExpanded ? 180 : 0 }}
                        className="text-slate-400"
                      >
                        <ChevronDown className="w-4 h-4" />
                      </motion.div>
                    </button>

                    {/* Card Expanded Content */}
                    <AnimatePresence>
                      {isItemExpanded && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: 'auto' }}
                          exit={{ height: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="px-3 pb-3 pt-0 space-y-3">
                            {/* Snippet */}
                            {item.snippet && (
                              <p className="text-sm text-slate-400 pl-11">
                                "{item.snippet}"
                              </p>
                            )}

                            {/* Actions */}
                            <div className="flex items-center gap-2 pl-11">
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
                              >
                                <ExternalLink className="w-4 h-4" />
                                Visit Source
                              </a>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
