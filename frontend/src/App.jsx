import { useState } from 'react';
import { StandardChat } from './components/StandardChat';

/**
 * Main App Component
 *
 * Holds the mode state for future dual-mode support:
 * - 'standard': ChatGPT-style professional interface
 * - 'animated': Fun retro computer with duck animations (coming soon)
 */
function App() {
  const [mode, setMode] = useState('standard');

  return (
    <div className="w-full h-screen">
      {mode === 'standard' && <StandardChat />}
      {/* Future: {mode === 'animated' && <AnimatedChat />} */}
    </div>
  );
}

export default App;
