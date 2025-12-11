# Check-It AI - Frontend Guide

## Quick Start

### Running the Application

**Terminal 1 - Start Backend:**
```bash
./scripts/run_api.sh
```
Backend runs at http://localhost:8000

**Terminal 2 - Start Frontend:**
```bash
./scripts/run_frontend.sh
```
Frontend runs at http://localhost:5173

## Architecture

```
Frontend (React + Vite + Tailwind)
├── App.jsx                    → Root component, mode state
├── components/
│   └── StandardChat.jsx       → ChatGPT-style interface
├── hooks/
│   └── useCheckItAI.js        → API communication hook
└── utils/
    └── cn.js                  → Tailwind class utility
```

## Tech Stack

- **React 19** - UI framework
- **Vite 7** - Build tool (fast HMR)
- **Tailwind CSS 3** - Styling
- **Axios** - HTTP client
- **React Markdown** - Message rendering
- **Lucide React** - Icons
- **Framer Motion** - Animations (ready for Phase 2B)

## Component Overview

### App.jsx
- Manages mode state (`standard` vs `animated`)
- Currently renders `StandardChat`
- Future: Toggle between standard/animated modes

### StandardChat.jsx
- **ChatGPT-style dark UI** with slate-900 background
- **Welcome screen** with example prompts
- **Message bubbles** - User (right, blue) vs AI (left, slate)
- **Evidence sidebar** - Collapsible panel with sources
- **Loading states** - Multi-stage indicators
- **Auto-scroll** - Jumps to latest message

### useCheckItAI Hook

**State:**
```javascript
{
  messages: [],           // Chat history
  isSearching: false,     // Phase 1: Searching sources
  isAnalyzing: false,     // Phase 2: Analyzing evidence
  isWriting: false,       // Phase 3: Writing response
  error: null,            // Error message
  currentEvidence: null   // Latest evidence bundle
}
```

**Methods:**
- `sendQuery(query)` - Send to API
- `clearMessages()` - Reset chat
- `getLoadingMessage()` - Current loading text

## API Integration

### Request
```javascript
POST http://localhost:8000/api/chat

{
  "query": "The Earth is round",
  "mode": "standard"
}
```

### Response
```javascript
{
  "answer": "Scientific consensus confirms...",
  "citations": [
    { "evidence_id": "E1", "url": "https://nasa.gov/..." }
  ],
  "evidence": {
    "items": [...],
    "overall_verdict": "supported"
  },
  "metadata": {
    "latency_ms": 45.2,
    "confidence": 0.98,
    "is_mock": true
  }
}
```

## Testing with Mock Mode

Use keywords to trigger different responses:
- `"mock:true ..."` → TRUE verdict (98% confidence)
- `"mock:false ..."` → FALSE verdict (95% confidence)
- `"mock:uncertain ..."` → UNCERTAIN (40% confidence)

**Example:**
```
Input: "mock:true The Earth is round"
Output: ✅ "Scientific consensus confirms Earth is round"
        Sources: NASA, National Geographic
```

## Styling

### Theme
- **Background**: `bg-slate-900` (#0f172a)
- **Cards**: `bg-slate-800` (#1e293b)
- **Primary**: `bg-blue-600` (#2563eb)
- **Text**: `text-slate-100` (white), `text-slate-400` (muted)

### Key Classes
```jsx
// Full dark background
<div className="bg-slate-900 text-slate-100">

// Message bubble
<div className="bg-slate-800 rounded-2xl p-4">

// User message
<div className="bg-blue-600 rounded-2xl p-4">

// Loading spinner
<Loader2 className="animate-spin text-blue-400" />
```

## Development

### Hot Module Replacement
- Edit any `.jsx` file → instant update
- No page refresh needed
- React Fast Refresh enabled

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   └── StandardChat.jsx
│   ├── hooks/
│   │   └── useCheckItAI.js
│   ├── utils/
│   │   └── cn.js
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css         ← Tailwind imports
├── public/
├── package.json
├── vite.config.js
└── tailwind.config.js    ← MUST include content paths!
```

### Important: Tailwind Config

**REQUIRED** for Tailwind to work:
```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",  // ← Critical!
  ],
  // ...
}
```

Without `content` paths, Tailwind won't scan your files → no styles!

## Common Issues

### White background instead of dark
**Cause:** Tailwind config missing content paths
**Fix:** Check `tailwind.config.js` has `content: ["./src/**/*.{js,jsx}"]`

### API connection fails
**Cause:** Backend not running or CORS issue
**Fix:**
1. Check backend: `curl http://localhost:8000/health`
2. Verify CORS in `server.py` includes `http://localhost:5173`

### Components not updating
**Cause:** Browser cache
**Fix:** Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## Build for Production

```bash
cd frontend
npm run build
```

Output: `frontend/dist/` (static files)

Deploy options:
- **Vercel/Netlify**: Deploy `dist/` folder
- **FastAPI**: Serve static files from backend
- **Docker**: Multi-stage build with backend

## Next Steps

### Phase 2B: Animated Mode
- Retro CRT screen aesthetic
- Animated hands typing
- Duck character for DuckDuckGo fallback
- Smoke effects for errors
- Toggle between standard/animated

### Real AI Integration
Replace mock service:
1. Implement `run_graph()` in `src/check_it_ai/graph/graph.py`
2. Update `/api/chat` endpoint to call real pipeline
3. Remove `is_mock: true` from metadata

## File Summary

| File | Purpose | Lines |
|------|---------|-------|
| `App.jsx` | Root component | ~20 |
| `StandardChat.jsx` | Main UI | ~300 |
| `useCheckItAI.js` | API hook | ~120 |
| `cn.js` | Utility | ~5 |
| `index.css` | Tailwind setup | ~35 |

**Total:** Clean, maintainable codebase under 500 lines!

## Resources

- **React Docs**: https://react.dev
- **Vite Docs**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Lucide Icons**: https://lucide.dev
- **Backend API**: http://localhost:8000/docs
