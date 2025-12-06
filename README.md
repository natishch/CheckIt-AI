# CheckIt-AI

An Agentic, Evidence-Grounded Historical Fact Verification Chat Application (LangGraph + Google Search API + Fine-Tuned LoRA LLM)

## Overview

CheckIt-AI is an AI-powered chat application that helps users verify historical facts by combining:
1. Live evidence retrieval via the Google Custom Search JSON API
2. An agentic workflow orchestrated with LangGraph
3. A custom fine-tuned LLM using PEFT/LoRA for improved truthfulness
4. A Streamlit UI presenting evidence, citations, and uncertainty estimates

## Project Structure

```
check-it-ai/
├── src/check_it_ai/          # Main package
│   ├── app/                  # Streamlit application
│   ├── graph/                # LangGraph workflow
│   │   └── nodes/            # Graph nodes (router, researcher, analyst, writer)
│   ├── tools/                # External tools (Google Search)
│   ├── llm/                  # LLM utilities and prompts
│   ├── training/             # LoRA fine-tuning code
│   ├── types/                # Pydantic schemas
│   └── utils/                # Utility functions
├── tests/                    # Test suite
├── data/                     # Data directories (raw, processed)
├── models/                   # Model storage (base, LoRA adapters)
├── notebooks/                # Jupyter notebooks for experiments
├── scripts/                  # Shell scripts
└── docs/                     # Documentation
```

## Setup

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd check-it-ai
```

2. Install dependencies:
```bash
uv sync
```

3. Install the package in editable mode:
```bash
uv pip install -e .
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

**Important: Google Search API Quota Limits**

The Google Custom Search JSON API has strict usage limits:
- **Free tier**: 100 queries per day
- **Paid tier**: Up to 10,000 queries per day (requires billing)

To handle quota limitations, this project includes two protective measures:

1. **Automatic Caching**: All search results are cached for 24 hours (configurable via `CACHE_TTL_HOURS`). This dramatically reduces API calls during development and demos.

2. **DuckDuckGo Fallback**: When the Google API quota is exceeded (HTTP 403/429 errors), the system can automatically fall back to DuckDuckGo search. Enable this in `.env`:
   ```bash
   USE_DUCKDUCKGO_BACKUP=true
   ```

**Recommendation for Development**: Keep caching enabled (default) and use `USE_DUCKDUCKGO_BACKUP=true` to ensure your demo works even if you hit quota limits.

### Running Tests

```bash
uv run pytest
```

### Running the Application

```bash
uv run streamlit run src/check_it_ai/app/streamlit_app.py
```

## Tech Stack

- **LangGraph**: Agentic workflow orchestration
- **Pydantic**: Type-safe schemas and validation
- **Streamlit**: Interactive web UI
- **PyTorch + Transformers**: Fine-tuning with PEFT/LoRA
- **Google Custom Search API**: Evidence retrieval
- **uv**: Fast dependency management

## Development

- **Linting**: `uv run ruff check .`
- **Type checking**: `uv run mypy src/`
- **Testing**: `uv run pytest`

## Working with AI Agents/Assistants

When using AI coding assistants (like Claude Code, GitHub Copilot, etc.) to work on this project, **start by having them read the documentation** to understand what's already been implemented.

### Recommended AI Agent Prompt

```
Please read all the documentation files in the docs/ folder to understand the current state of the check-it-ai project:

- docs/INITIALIZATION_SUMMARY.md - Initial project setup
- docs/AH_02_CORE_SCHEMAS_SUMMARY.md - Core Pydantic schemas and state
- docs/AH_03_04_CONFIG_CACHING_GOOGLE_SEARCH.md - Configuration and Google Search tool
- docs/technical_design.pdf - Complete system architecture
- docs/tasks_playbook.pdf - Task breakdown and guidance

Important: This project uses the package name `check_it_ai` (not `agentic_historian`).
```

### Key Points for AI Assistants
- **Package naming**: Always use `check_it_ai` in imports (the PDF mentions `agentic_historian`, but we renamed it)
- **Python version**: 3.12+
- **Dependency manager**: `uv` (not pip or poetry)
- **Testing**: Run `uv run pytest` after any changes
- **Code quality**: Run `uv run ruff check .` before committing

## License

See [LICENSE.txt](LICENSE.txt)