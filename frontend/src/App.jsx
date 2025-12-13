import { useState } from 'react';
import { TrustEngine } from './components/TrustEngine';
import { StandardChat } from './components/StandardChat';

/**
 * Main App Component
 *
 * Holds the mode state for dual-mode support:
 * - 'trust': New Trust Engine interface (default)
 * - 'standard': ChatGPT-style professional interface
 */
function App() {
  const [mode, setMode] = useState('trust');

  return (
    <div className="w-full h-screen bg-zinc-950">
      {mode === 'trust' && <TrustEngine />}
      {mode === 'standard' && <StandardChat />}
    </div>
  );
}

export default App;