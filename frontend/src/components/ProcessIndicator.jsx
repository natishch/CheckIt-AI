import { motion } from 'framer-motion';
import { Router, Search, BarChart3, PenTool, CheckCircle2 } from 'lucide-react';
import { cn } from '../utils/cn';

/**
 * ProcessIndicator Component
 *
 * Shows the pipeline step visibility:
 * Router → Researcher → Analyst → Writer
 *
 * Builds trust by showing work is actually happening.
 */
export const ProcessIndicator = ({
  currentStep = null,
  completedSteps = [],
  isComplete = false
}) => {
  const steps = [
    { id: 'router', label: 'Router', icon: Router, description: 'Analyzing query...' },
    { id: 'researcher', label: 'Researcher', icon: Search, description: 'Searching sources...' },
    { id: 'analyst', label: 'Analyst', icon: BarChart3, description: 'Analyzing evidence...' },
    { id: 'writer', label: 'Writer', icon: PenTool, description: 'Writing response...' },
  ];

  const getStepStatus = (stepId) => {
    if (isComplete) return 'completed';
    if (completedSteps.includes(stepId)) return 'completed';
    if (currentStep === stepId) return 'active';
    return 'pending';
  };

  return (
    <div className="py-6">
      {/* Steps Container */}
      <div className="flex items-center justify-center gap-2">
        {steps.map((step, idx) => {
          const status = getStepStatus(step.id);
          const StepIcon = step.icon;
          const isLast = idx === steps.length - 1;

          return (
            <div key={step.id} className="flex items-center">
              {/* Step Circle */}
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: idx * 0.1 }}
                className="flex flex-col items-center"
              >
                <motion.div
                  className={cn(
                    "w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300",
                    status === 'completed' && "bg-green-500/20 border-2 border-green-500",
                    status === 'active' && "bg-blue-500/20 border-2 border-blue-500",
                    status === 'pending' && "bg-slate-800 border-2 border-slate-600"
                  )}
                  animate={status === 'active' ? {
                    boxShadow: ['0 0 0 0 rgba(59, 130, 246, 0.4)', '0 0 0 10px rgba(59, 130, 246, 0)'],
                  } : {}}
                  transition={status === 'active' ? {
                    duration: 1.5,
                    repeat: Infinity,
                  } : {}}
                >
                  {status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                  ) : (
                    <StepIcon className={cn(
                      "w-5 h-5",
                      status === 'active' ? "text-blue-400" : "text-slate-500"
                    )} />
                  )}
                </motion.div>

                {/* Step Label */}
                <motion.span
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 + 0.1 }}
                  className={cn(
                    "mt-2 text-xs font-medium",
                    status === 'completed' && "text-green-400",
                    status === 'active' && "text-blue-400",
                    status === 'pending' && "text-slate-500"
                  )}
                >
                  {step.label}
                </motion.span>

                {/* Active Step Description */}
                {status === 'active' && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-1 text-xs text-slate-400"
                  >
                    {step.description}
                  </motion.span>
                )}
              </motion.div>

              {/* Connector Line */}
              {!isLast && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: idx * 0.1 + 0.05 }}
                  className={cn(
                    "w-8 h-0.5 mx-2 origin-left",
                    completedSteps.includes(step.id) || isComplete
                      ? "bg-green-500"
                      : currentStep === step.id
                        ? "bg-blue-500"
                        : "bg-slate-700"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Overall Progress Message */}
      {!isComplete && currentStep && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 text-center"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-full border border-slate-700">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"
            />
            <span className="text-sm text-slate-300">
              {steps.find(s => s.id === currentStep)?.description || 'Processing...'}
            </span>
          </div>
        </motion.div>
      )}

      {/* Complete State */}
      {isComplete && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mt-6 text-center"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-500/10 rounded-full border border-green-500/50">
            <CheckCircle2 className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400">Analysis Complete</span>
          </div>
        </motion.div>
      )}
    </div>
  );
};
