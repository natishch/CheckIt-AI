# AH-03 + AH-04: Configuration, Caching & Google Search Tool - Implementation Summary

**Task**: Implement Configuration, Logging, Caching, and Google Search Tool
**Date**: 2025-12-06
**Status**: ✅ Completed
**Branch**: ah-02-core-schemas-shared-langgraph-state-pydantic

---

## Overview

This task implemented the foundational infrastructure for the check-it-ai system, including:
1. Type-safe configuration management using pydantic-settings
2. Structured logging system
3. JSON file-based caching for search results (critical for API quota management)
4. Full-featured Google Custom Search API client with fallback support

All implementations follow production-ready best practices with comprehensive error handling, validation, and testing.

---

## What Was Implemented

### 1. Configuration Module ([src/check_it_ai/config.py](src/check_it_ai/config.py))

**Technology**: `pydantic-settings` for type-safe environment variable loading

**Key Features**:
- Type-safe Settings class with validation
- Automatic `.env` file loading
- Default values for all settings
- Automatic directory creation for cache and models

**Settings Implemented**:
```python
# Google Custom Search API
- google_api_key: str
- google_cse_id: str

# Search Configuration
- use_duckduckgo_backup: bool (default: False)
- max_search_results: int (default: 10, range: 1-100)
- search_timeout: int (default: 30 seconds, range: 1-120)

# Application Configuration
- log_level: str (default: "INFO")
- cache_dir: Path (default: "./cache")
- model_dir: Path (default: "./models")

# Cache Configuration
- cache_ttl_hours: int (default: 24 hours)
```

**Usage**:
```python
from check_it_ai.config import settings

api_key = settings.google_api_key
cache_dir = settings.cache_dir
```

---

### 2. Structured Logging ([src/check_it_ai/utils/logging.py](src/check_it_ai/utils/logging.py))

**Features**:
- Custom `StructuredFormatter` for enhanced log output
- `setup_logger()` function for consistent logger configuration
- `log_with_context()` for adding extra context fields to logs
- Global `app_logger` instance

**Log Format**:
```
2025-12-06 14:30:45 | check_it_ai.tools.google_search | INFO | google_search.py:96 | Fetching search results from Google API: World War II
```

**Usage**:
```python
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)
logger.info("Cache hit: World War II", extra={"cache_key": "abc123", "num_results": 10})
```

---

### 3. Search Cache ([src/check_it_ai/utils/cache.py](src/check_it_ai/utils/cache.py))

**Purpose**: Save Google API quota during development and demos

**Implementation**:
- JSON file-based storage
- SHA256 hash keys from query + num_results
- TTL-based expiration (default: 24 hours)
- Automatic cleanup of corrupted/expired files

**Key Methods**:
- `get(query, num_results)`: Retrieve cached results (returns None on miss/expiry)
- `set(query, results, num_results)`: Store results in cache
- `clear()`: Remove all cache files
- `clear_expired()`: Remove only expired files

**Cache Structure**:
```json
{
  "query": "World War II",
  "num_results": 10,
  "timestamp": "2025-12-06T14:30:45.123456",
  "results": [
    {
      "title": "World War II - Wikipedia",
      "snippet": "World War II ended in 1945...",
      "link": "https://en.wikipedia.org/wiki/World_War_II",
      "displayLink": "en.wikipedia.org"
    }
  ]
}
```

**Usage**:
```python
from check_it_ai.utils.cache import search_cache

# Check cache
cached = search_cache.get("World War II", num_results=10)
if cached is None:
    # Fetch from API and cache
    results = fetch_from_api("World War II")
    search_cache.set("World War II", results, num_results=10)
```

---

### 4. Google Search Client ([src/check_it_ai/tools/google_search.py](src/check_it_ai/tools/google_search.py))

**Full-Featured Functional API with**:
- Automatic caching (checks cache before API call)
- Quota error handling (429, 403 status codes)
- Optional DuckDuckGo fallback (configurable)
- Pydantic model normalization (raw JSON → SearchResult models)
- Input validation
- Comprehensive error handling and logging

**Key Components**:
- `QuotaError`: Custom exception for API quota exhaustion
- `google_search()`: Main search function (functional API)
- `GoogleSearchClient`: Backwards compatibility wrapper class (deprecated)
- Helper functions: `_fetch_from_google()`, `_fallback_search()`, `_parse_results()`

**Design**: Functional-first approach with clean parameter passing instead of class-based state management.

**Search Flow**:
```
1. Validate query and num_results
2. Check cache → if hit, return cached results
3. If cache miss:
   a. Call Google Custom Search JSON API
   b. Handle quota errors (403/429):
      - If fallback enabled → try DuckDuckGo
      - Otherwise → raise QuotaError
   c. Parse JSON response → SearchResult models
   d. Cache valid results
4. Return list[SearchResult]
```

**Usage** (recommended functional API):
```python
from check_it_ai.tools.google_search import google_search

# Simple usage with defaults
results = google_search("World War II", num_results=10)

# Custom configuration
results = google_search(
    "World War II",
    num_results=10,
    api_key="custom_key",
    use_fallback=True
)

for result in results:
    print(f"{result.rank}. {result.title}")
    print(f"   {result.snippet}")
    print(f"   {result.url}")
```

**Usage** (legacy class API - still supported):
```python
from check_it_ai.tools.google_search import GoogleSearchClient

client = GoogleSearchClient()
results = client.search("World War II", num_results=10)
```

**Error Handling**:
- `ValueError`: Empty query or invalid num_results
- `QuotaError`: Google API quota exceeded (no fallback)
- `httpx.TimeoutException`: Request timeout
- `httpx.HTTPError`: Other HTTP errors

---

## Environment Configuration

### Updated [.env.example](.env.example)

```bash
# Google Custom Search API Configuration
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here

# Search Engine Fallback
USE_DUCKDUCKGO_BACKUP=false

# Application Configuration
LOG_LEVEL=INFO
CACHE_DIR=./cache
MODEL_DIR=./models

# Search Configuration
MAX_SEARCH_RESULTS=10
SEARCH_TIMEOUT=30

# Cache Configuration
CACHE_TTL_HOURS=24
```

**Setup Instructions**:
1. Copy `.env.example` to `.env`
2. Get Google API key: https://developers.google.com/custom-search/v1/introduction
3. Create Custom Search Engine: https://programmablesearchengine.google.com/
4. Add credentials to `.env`

---

## Testing

### Test Suite ([tests/test_google_tool.py](tests/test_google_tool.py))

**12 comprehensive tests** covering:

#### Input Validation (3 tests)
- ✅ Client initialization with correct parameters
- ✅ Empty query rejection
- ✅ Invalid num_results rejection (0, 101)

#### API Integration (3 tests)
- ✅ Successful Google search with mocked response
- ✅ Quota error handling (403 status)
- ✅ Quota error handling (429 status)

#### Caching Mechanism (3 tests)
- ✅ Cache hit (no API call on second request)
- ✅ Cache miss on different query
- ✅ Fallback triggered on quota error (when enabled)

#### Error Handling (2 tests)
- ✅ HTTP timeout error propagation
- ✅ Invalid search results skipped during parsing

#### Edge Cases (1 test)
- ✅ Empty search results from API

**Test Coverage Summary**:
- Mocked `httpx` for API simulation
- Temporary cache directories for isolation
- All search flow paths tested
- Error conditions thoroughly covered

---

## Dependencies Added

```toml
[project.dependencies]
pydantic-settings = "^2.12.0"  # Type-safe configuration
ddgs = "^1.3.1"                 # DuckDuckGo fallback search engine
```

Existing dependencies used:
- `httpx` - HTTP client for Google API
- `pydantic` - Data validation (SearchResult models)
- `python-dotenv` - Environment variable loading (via pydantic-settings)

---

## Key Technical Decisions

### 1. Pydantic-Settings for Configuration
**Rationale**:
- Type-safe configuration with validation
- Automatic env var loading and type conversion
- Default values and field constraints
- Better IDE support than plain `os.getenv()`

### 2. JSON File-Based Cache
**Rationale**:
- Simple, no external dependencies (Redis, etc.)
- Easy to inspect and debug
- Sufficient for demo/development use
- Automatic cleanup of expired/corrupted files

**Trade-offs**:
- Not suitable for production at scale
- No distributed cache support
- File I/O overhead (minimal for our use case)

### 3. SHA256 Hash for Cache Keys
**Rationale**:
- Deterministic: same query + num_results → same hash
- Case-insensitive (query is lowercased)
- Handles special characters safely
- No collision risk for practical use

### 4. Quota Error as Custom Exception
**Rationale**:
- Distinct from generic HTTP errors
- Enables specific handling (fallback logic)
- Clear intent in code (`except QuotaError`)
- Better error messages

### 5. DuckDuckGo Fallback (Fully Implemented)
**Rationale**:
- Demo reliability when quota exhausted
- Configurable via `USE_DUCKDUCKGO_BACKUP` env var
- Automatically triggers on Google API quota errors (403/429)
- Uses `ddgs` library for actual search
- Converts DuckDuckGo results to same `SearchResult` Pydantic models
- Graceful error handling with comprehensive logging

### 6. Functional Design (Refactored)
**Rationale**:
- Simpler code - no unnecessary class state
- More explicit - all dependencies passed as parameters
- Easier testing - pure functions are simpler to mock
- Backwards compatible - legacy `GoogleSearchClient` class wrapper maintained

---

## Integration with Existing Code

### With AH-02 Schemas
The Google Search function seamlessly integrates with schemas from AH-02:

```python
from check_it_ai.types.schemas import SearchResult
from check_it_ai.tools.google_search import google_search

# Functional API (recommended)
results: list[SearchResult] = google_search("World War II")

# SearchResult Pydantic models are validated
assert all(isinstance(r, SearchResult) for r in results)
assert results[0].rank == 1
assert str(results[0].url).startswith("https://")

# Legacy class API (still works)
from check_it_ai.tools.google_search import GoogleSearchClient
client = GoogleSearchClient()
results = client.search("World War II")
```

### With Future Nodes

**Researcher Node** (`graph/nodes/researcher.py`) will use:
```python
from check_it_ai.tools.google_search import google_search
from check_it_ai.graph.state import AgentState

def researcher_node(state: AgentState) -> AgentState:
    # Execute search queries using functional API
    all_results = []
    for query in state.search_queries:
        results = google_search(query.query, num_results=query.max_results)
        all_results.extend(results)

    # Return state delta
    return AgentState(search_results=all_results)
```

---

## File Summary

### Created Files
- ✅ [src/check_it_ai/config.py](src/check_it_ai/config.py) (85 lines)
- ✅ [src/check_it_ai/utils/logging.py](src/check_it_ai/utils/logging.py) (93 lines)
- ✅ [src/check_it_ai/utils/cache.py](src/check_it_ai/utils/cache.py) (207 lines)
- ✅ [src/check_it_ai/tools/google_search.py](src/check_it_ai/tools/google_search.py) (332 lines - refactored to functional design)
- ✅ [tests/test_google_tool.py](tests/test_google_tool.py) (292 lines)
- ✅ [docs/AH_03_04_CONFIG_CACHING_GOOGLE_SEARCH.md](docs/AH_03_04_CONFIG_CACHING_GOOGLE_SEARCH.md) (this file)

### Modified Files
- ✅ [.env.example](.env.example) - Added new environment variables

### Refactored Files
- ✅ [src/check_it_ai/tools/google_search.py](src/check_it_ai/tools/google_search.py) - Converted from class-based to functional design with backwards-compatible wrapper

---

## Verification Checklist

- ✅ All 45 total tests pass (12 new + 33 existing)
- ✅ Ruff linting passes with no errors
- ✅ All imports use `check_it_ai` package
- ✅ Type hints complete and accurate
- ✅ Docstrings on all classes and methods
- ✅ Logging uses `extra` parameter for structured data
- ✅ Cache functionality verified with tests
- ✅ Quota handling tested (403, 429 errors)
- ✅ Settings validation works correctly
- ✅ Files have trailing newlines (ruff W292)
- ✅ No f-strings without placeholders (ruff F541)

---

## Running the Code

### Basic Usage (Functional API - Recommended)

```python
from check_it_ai.tools.google_search import google_search

# Simple search (uses cache if available)
results = google_search("When did World War II end?", num_results=5)

# Display results
for result in results:
    print(f"[{result.rank}] {result.title}")
    print(f"    {result.snippet}")
    print(f"    {result.url}")
    print()
```

### Legacy Class API (Still Supported)

```python
from check_it_ai.tools.google_search import GoogleSearchClient

# Initialize client
client = GoogleSearchClient()

# Search (uses cache if available)
results = client.search("When did World War II end?", num_results=5)

# Display results
for result in results:
    print(f"[{result.rank}] {result.title}")
    print(f"    {result.snippet}")
    print(f"    {result.url}")
    print()
```

### Running Tests

```bash
# Run all tests
uv run pytest -v

# Run only Google tool tests
uv run pytest tests/test_google_tool.py -v

# Run with coverage
uv run pytest --cov=src/check_it_ai --cov-report=html
```

### Linting

```bash
# Check code quality
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/
```

---

## Common Usage Patterns

### Pattern 1: Using the Global Cache Instance
```python
from check_it_ai.utils.cache import search_cache

# Check cache
results = search_cache.get("World War II")
if results is None:
    # Fetch and cache
    results = fetch_from_somewhere()
    search_cache.set("World War II", results)
```

### Pattern 2: Custom Cache Instance
```python
from check_it_ai.utils.cache import SearchCache
from pathlib import Path

# Create custom cache
custom_cache = SearchCache(
    cache_dir=Path("./my_cache"),
    ttl_hours=48  # 2 days
)

results = custom_cache.get("query")
```

### Pattern 3: Handling Quota Errors
```python
from check_it_ai.tools.google_search import GoogleSearchClient, QuotaError

client = GoogleSearchClient(use_fallback=False)

try:
    results = client.search("query")
except QuotaError:
    # Handle quota exhaustion
    print("API quota exceeded. Try again later.")
except ValueError as e:
    # Handle validation errors
    print(f"Invalid input: {e}")
```

---

## Next Steps

### For AH-05: Implement Researcher Node
With this infrastructure in place, you can now:

1. **Create Researcher Node**:
   ```python
   from check_it_ai.tools.google_search import GoogleSearchClient
   from check_it_ai.graph.state import AgentState

   def researcher_node(state: AgentState) -> AgentState:
       client = GoogleSearchClient()
       results = client.search(state.user_query, num_results=10)
       return AgentState(search_results=results)
   ```

2. **Add Query Expansion**: Generate multiple search queries from user input

3. **Implement Domain Filtering**: Restrict searches to `.edu`, `.gov`, etc.

### For AH-06: Production Enhancements

1. **Add Redis Caching** (optional):
   - Replace file-based cache with Redis
   - Better for production/distributed systems

2. **Rate Limiting**:
   - Track API usage
   - Implement exponential backoff

---

## Troubleshooting

### Issue: "Google API credentials not configured" warning
**Solution**: Add `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` to `.env` file

### Issue: QuotaError during development
**Solution**:
1. Enable caching (already enabled by default)
2. Set `USE_DUCKDUCKGO_BACKUP=true` in `.env`
3. Use cached data from previous runs

### Issue: Cache not working
**Solution**:
1. Check cache directory exists and is writable
2. Verify `CACHE_DIR` in `.env`
3. Check cache TTL hasn't expired

### Issue: Timeout errors
**Solution**:
1. Increase `SEARCH_TIMEOUT` in `.env`
2. Check network connectivity
3. Verify Google API endpoint is accessible

---

## References

- **Technical Design**: `docs/technical_design.pdf` (Section 3.3, 5)
- **AH-02 Summary**: `docs/AH_02_CORE_SCHEMAS_SUMMARY.md`
- **Google Custom Search API**: https://developers.google.com/custom-search/v1/introduction
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **httpx Documentation**: https://www.python-httpx.org/

---

## Questions for Next Developer

1. Should we implement distributed caching (Redis) for production?
2. Should we add retry logic with exponential backoff?
3. Do we need to track API quota usage in metadata?
4. Should we implement domain filtering in the search client or researcher node?
5. Do we want to support multiple search engines (Bing, etc.)?

---

## AH-04 (Continued): Google Fact Check Tools API Integration

**Date Added**: 2025-12-09
**Status**: ✅ Completed

### Overview

As an enhancement to the Google Search infrastructure, we implemented the **Google Fact Check Tools API** as a parallel evidence source. This enables the system to leverage professional fact-checking work from organizations like PolitiFact, Snopes, FactCheck.org, and 100+ other ClaimReview publishers.

**Key Decision**: Both APIs work in parallel (multi-source strategy) rather than one-or-the-other, allowing the Researcher Node to gather evidence from both professional fact-checkers AND general web sources.

### Implementation

**File**: [src/check_it_ai/tools/fact_check_api.py](../src/check_it_ai/tools/fact_check_api.py)

**Features**:
- Functional API design matching `google_search.py` pattern
- Automatic caching with 24-hour TTL (uses "factcheck_" prefix to avoid collision)
- Quota error handling (403, 429 status codes)
- Graceful degradation on failures (returns empty list)
- Pydantic model normalization (raw JSON → SearchResult)
- Backwards-compatible class wrapper (`FactCheckClient`)

**Key Function**:

```python
def google_fact_check(
    query: str,
    num_results: int = 10,
    api_key: str | None = None,
    language_code: str = "en",
    cache: SearchCache | None = None,
) -> list[SearchResult]:
    """Search using Google Fact Check Tools API with caching."""
```

### Response Normalization

All fact-check results are normalized to `SearchResult` schema for consistency:
- Title prefixed with `[FACT-CHECK]` for easy identification
- Rating included in snippet: "Rating: True | Fact-check title"
- Publisher name used as `display_domain`
- Same caching and error handling as Google Search

### Configuration Updates

Added to [src/check_it_ai/config.py](../src/check_it_ai/config.py:38):

```python
use_fact_check_api: bool = Field(
    default=True,
    description="Enable Google Fact Check Tools API for professional fact-checks",
)
```

Added to [.env.example](.env.example:11):

```bash
# Enable Google Fact Check Tools API (true/false)
# Uses same GOOGLE_API_KEY as Custom Search
USE_FACT_CHECK_API=true
```

### Testing

**File**: [tests/test_fact_check_api.py](../tests/test_fact_check_api.py)

**Test Coverage (13 tests)**:
- Client initialization
- Input validation (empty query, invalid num_results)
- API integration (successful search, empty results)
- Quota error handling (403, 429)
- Caching behavior (hit, miss)
- Error handling (timeout, malformed claims)
- Data normalization ([FACT-CHECK] prefix, rating in snippet)

**All 58 total tests pass** (13 new + 45 existing)

### Multi-Source Strategy for Researcher Node (AH-06)

When implementing the Researcher Node, use both APIs:

```python
def researcher_node(state: AgentState) -> AgentState:
    """Multi-source evidence gathering."""
    all_results = []

    for query in queries:
        # Source 1: Fact Check API
        if settings.use_fact_check_api:
            try:
                fact_checks = google_fact_check(query, num_results=5)
                all_results.extend(fact_checks)
            except Exception as e:
                logger.warning(f"Fact Check API failed: {e}")

        # Source 2: Google Custom Search
        try:
            search_results = google_search(query, num_results=10)
            all_results.extend(search_results)
        except Exception as e:
            logger.error(f"Google Search failed: {e}")

    # Deduplicate by URL
    deduped = deduplicate_by_url(all_results)

    state.search_results = deduped
    state.run_metadata["researcher"] = {
        "num_fact_checks": sum(1 for r in deduped if "[FACT-CHECK]" in r.title),
        "num_web_sources": len(deduped) - num_fact_checks,
    }
    return state
```

### Enhanced Fact Analyst Integration (AH-07)

The Fact Analyst should prioritize fact-checker sources:

**Tiered Credibility Scoring**:
- Tier 1 (score=10): Professional fact-checkers (detected by `[FACT-CHECK]` prefix)
- Tier 2 (score=5): Authoritative domains (.gov, .edu)
- Tier 3 (score=1): General web sources

**Verdict Detection**:
Extract fact-checker ratings from snippets:
- "Rating: False" / "Rating: True" / "Rating: Mixture"
- Use fact-checker verdict to inform overall verdict
- If fact-checkers say "not_supported", trust them

### API Documentation

**Endpoint**: `https://factchecktools.googleapis.com/v1alpha1/claims:search`

**Authentication**: Same API key as Google Custom Search

**Common Textual Ratings**:
- "True" / "Correct" / "Accurate"
- "False" / "Incorrect" / "Inaccurate"
- "Mixture" / "Partly True" / "Mostly False"
- "Unproven" / "Unverified"

**Rate Limits**: Same as Google Custom Search (100 queries/day free, 10,000/day paid)

**Getting Access**:
1. Same API key as Google Custom Search
2. Enable "Fact Check Tools API" in Google Cloud Console
3. No separate CSE ID needed

### Files Modified/Created

**Created**:
- [src/check_it_ai/tools/fact_check_api.py](../src/check_it_ai/tools/fact_check_api.py) (320 lines)
- [tests/test_fact_check_api.py](../tests/test_fact_check_api.py) (385 lines)

**Modified**:
- [src/check_it_ai/config.py](../src/check_it_ai/config.py) - Added `use_fact_check_api` setting
- [.env.example](.env.example) - Added Fact Check API configuration

### Benefits of Multi-Source Approach

1. **Richer Evidence Pool**: More sources = better analysis
2. **Cross-Validation**: Compare fact-checker verdicts vs general web consensus
3. **Enhanced Contradiction Detection**: Detect when professionals disagree with popular sources
4. **Improved User Trust**: Show both fact-checker ratings AND general sources
5. **Resilience**: System works even if one API fails

---

## AH-04 Refactoring: Code Deduplication and Separation of Concerns

**Date**: 2025-12-10
**Status**: ✅ Completed

### Overview

Following the implementation of Google Search and Fact Check API, we identified code duplication between search tools and improper coupling of fallback logic. This refactoring improved code quality, separation of concerns, and maintainability.

### Problems Addressed

1. **Code Duplication**: Both `google_search.py` and `fact_check_api.py` had ~50 lines of duplicated HTTP request and quota error handling code
2. **Separation of Concerns**: Search tools contained orchestration logic (fallback to DuckDuckGo) that should belong in the Researcher Node
3. **Maintainability**: Changes to error handling required updates in multiple files

### Refactoring Changes

#### 1. Created Shared HTTP Utilities

**File**: [src/check_it_ai/tools/_http_utils.py](../src/check_it_ai/tools/_http_utils.py) (75 lines)

**Purpose**: Centralize HTTP request logic and quota error handling across all search tools

**Key Components**:

```python
class QuotaExceededError(Exception):
    """Base exception for API quota errors across all search providers.

    Raised when any search API (Google Search, Fact Check, etc.)
    returns a quota exceeded error (typically HTTP 403 or 429).
    """
    pass


def make_api_request(
    url: str,
    params: dict,
    timeout: int | None = None,
    quota_statuses: tuple[int, ...] = (403, 429),
) -> dict:
    """Make HTTP GET request with standardized quota error handling.

    This utility provides consistent error handling across all search tools.
    Automatically detects quota exceeded errors and raises QuotaExceededError.

    Args:
        url: API endpoint URL
        params: Query parameters for the GET request
        timeout: Request timeout in seconds (uses settings.search_timeout if None)
        quota_statuses: HTTP status codes indicating quota exceeded (default: 403, 429)

    Returns:
        Parsed JSON response as dictionary

    Raises:
        QuotaExceededError: If response status code is in quota_statuses
        httpx.TimeoutException: If request times out
        httpx.HTTPError: For other HTTP errors
    """
```

**Benefits**:
- Single source of truth for HTTP error handling
- Consistent error messages across all search tools
- Reduced code duplication (~50 lines per tool)
- Easier to maintain and test

#### 2. Separated DuckDuckGo Search Provider

**File**: [src/check_it_ai/tools/duckduckgo_search.py](../src/check_it_ai/tools/duckduckgo_search.py) (100 lines)

**Rationale**: DuckDuckGo is a **standalone search provider**, not a fallback feature of Google Search. The Researcher Node should decide which provider(s) to use and when.

**Function**:
```python
def duckduckgo_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """Search using DuckDuckGo as a fallback search provider.

    This function is provided as a standalone search provider for use by the
    researcher node (AH-06) when Google Search or Fact Check API quota is exceeded.

    DuckDuckGo does not require API keys and has no quota limits, making it
    an ideal fallback option.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of SearchResult Pydantic models

    Raises:
        ValueError: If query is empty
    """
```

**Key Features**:
- No API keys required (quota-free)
- Same `SearchResult` output format as other providers
- Graceful error handling (returns empty list on failure)
- Comprehensive logging

**Test Coverage**: [tests/unit/test_duckduckgo_search.py](tests/unit/test_duckduckgo_search.py) (6 tests)

#### 3. Refactored Google Search Tool

**File**: [src/check_it_ai/tools/google_search.py](../src/check_it_ai/tools/google_search.py)

**Changes**:
1. Removed `use_fallback` parameter (was coupling search tool with orchestration logic)
2. Removed `_fallback_search()` function (77 lines) - moved to standalone `duckduckgo_search.py`
3. Refactored `_fetch_from_google()` to use shared `make_api_request()` utility
4. Changed `QuotaError` to alias of `QuotaExceededError` for backwards compatibility
5. Updated docstrings to note fallback logic moved to Researcher Node (AH-06)

**Before** (coupled design):
```python
def google_search(query: str, use_fallback: bool = False) -> list[SearchResult]:
    try:
        results = _fetch_from_google(query)
    except QuotaError:
        if use_fallback:
            return _fallback_search(query)  # Orchestration logic in search tool
        raise
```

**After** (clean separation):
```python
def google_search(query: str) -> list[SearchResult]:
    """Search using Google Custom Search API with caching.

    Note: This function no longer handles DuckDuckGo fallback internally.
    Fallback logic should be implemented in the researcher node (AH-06) for
    better separation of concerns.
    """
    # Uses shared make_api_request() utility
    data = make_api_request(GOOGLE_SEARCH_API_URL, params)
    return _parse_results(data.get("items", []))
```

#### 4. Refactored Fact Check API Tool

**File**: [src/check_it_ai/tools/fact_check_api.py](../src/check_it_ai/tools/fact_check_api.py)

**Changes**:
1. Refactored `_fetch_from_fact_check_api()` to use shared `make_api_request()` utility
2. Changed `FactCheckQuotaError` from custom exception to simple alias: `FactCheckQuotaError = QuotaExceededError`
3. Updated all docstring references to use `QuotaExceededError`
4. Removed duplicated HTTP error handling code (~50 lines)

**Before**:
```python
class FactCheckQuotaError(Exception):
    """Custom exception for Fact Check API quota errors."""
    pass

def _fetch_from_fact_check_api(...):
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        if response.status_code in (403, 429):
            # Duplicated error handling logic
            raise FactCheckQuotaError(...)
        response.raise_for_status()
        return response.json()
```

**After**:
```python
# Simple alias for backwards compatibility
FactCheckQuotaError = QuotaExceededError

def _fetch_from_fact_check_api(...):
    # Uses shared utility - no duplicated error handling
    data = make_api_request(FACT_CHECK_API_URL, params)
    return data.get("claims", [])
```

### Test Updates

**Files Modified**:
- [tests/test_google_tool.py](../tests/test_google_tool.py) - Removed fallback test, updated quota error tests
- [tests/test_fact_check_api.py](../tests/test_fact_check_api.py) - Updated quota error assertions

**Files Created**:
- [tests/test_duckduckgo_search.py](../tests/test_duckduckgo_search.py) - 6 comprehensive tests

**Test Results**: All 63 tests pass

### Architecture: Search Tools vs Orchestration

**Key Principle**: Search tools are **"dumb" data fetchers**; nodes are **"smart" orchestrators**

#### Search Tool Responsibilities (What They SHOULD Do)
✅ Fetch data from ONE specific source
✅ Normalize response to `SearchResult` schema
✅ Handle source-specific errors (quota, timeout, malformed data)
✅ Use caching to reduce API calls
✅ Return empty list on graceful failures

#### Search Tool Anti-Patterns (What They SHOULD NOT Do)
❌ Decide which source to query based on context
❌ Implement fallback chains (call provider B if provider A fails)
❌ Orchestrate multiple providers
❌ Determine query strategy (parallel vs sequential)
❌ Weight or rank results from different sources

#### Researcher Node Responsibilities (AH-06)
The Researcher Node should handle:
- Multi-source orchestration (Google, Fact Check, DuckDuckGo)
- Fallback strategy when quota exceeded
- Parallel vs sequential query execution
- Result deduplication by URL
- Metadata tracking (source counts, cache hits, etc.)

---

## Suggestions for Future Tasks

### AH-06: Researcher Node - Multi-Source Search Strategy

**Recommendation**: Implement parallel multi-source evidence gathering with configurable fallback chain

#### Suggested Implementation Pattern

```python
from check_it_ai.tools.google_search import google_search
from check_it_ai.tools.fact_check_api import google_fact_check
from check_it_ai.tools.duckduckgo_search import duckduckgo_search
from check_it_ai.tools._http_utils import QuotaExceededError

def researcher_node(state: AgentState) -> AgentState:
    """Multi-source evidence gathering with fallback chain."""
    all_results = []
    metadata = {
        "fact_check_used": False,
        "google_used": False,
        "duckduckgo_used": False,
        "quota_exceeded": False,
    }

    for query in state.search_queries:
        query_results = []

        # TIER 1: Professional fact-checkers (highest priority)
        if settings.use_fact_check_api:
            try:
                # Try default language first
                fact_checks = google_fact_check(
                    query.query,
                    num_results=5,
                    language_code=settings.default_language
                )

                # Language fallback: If no results and languages differ, try fallback
                if not fact_checks and settings.default_language != settings.fallback_language:
                    logger.info(
                        f"No fact-checks in {settings.default_language}, trying {settings.fallback_language}"
                    )
                    fact_checks = google_fact_check(
                        query.query,
                        num_results=5,
                        language_code=settings.fallback_language
                    )
                    metadata["language_fallback_used"] = True

                query_results.extend(fact_checks)
                metadata["fact_check_used"] = True
                logger.info(f"Fact Check API: {len(fact_checks)} results")
            except QuotaExceededError:
                logger.warning("Fact Check API quota exceeded")
                metadata["quota_exceeded"] = True
            except Exception as e:
                logger.error(f"Fact Check API failed: {e}")

        # TIER 2: Google Custom Search (high-quality web sources)
        try:
            google_results = google_search(query.query, num_results=10)
            query_results.extend(google_results)
            metadata["google_used"] = True
            logger.info(f"Google Search: {len(google_results)} results")
        except QuotaExceededError:
            logger.warning("Google Search quota exceeded, falling back to DuckDuckGo")
            metadata["quota_exceeded"] = True

            # TIER 3: DuckDuckGo fallback (quota-free, lower quality)
            try:
                ddg_results = duckduckgo_search(query.query, num_results=10)
                query_results.extend(ddg_results)
                metadata["duckduckgo_used"] = True
                logger.info(f"DuckDuckGo: {len(ddg_results)} results")
            except Exception as e:
                logger.error(f"DuckDuckGo fallback failed: {e}")
        except Exception as e:
            logger.error(f"Google Search failed: {e}")

        all_results.extend(query_results)

    # Deduplicate by URL
    deduped_results = _deduplicate_by_url(all_results)

    # Update state
    state.search_results = deduped_results
    state.run_metadata["researcher"] = metadata

    logger.info(
        f"Researcher gathered {len(deduped_results)} unique results from {len(all_results)} total",
        extra=metadata
    )

    return state


def _deduplicate_by_url(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate results by URL, keeping first occurrence."""
    seen_urls = set()
    unique_results = []

    for result in results:
        url_str = str(result.url).lower()
        if url_str not in seen_urls:
            seen_urls.add(url_str)
            unique_results.append(result)

    return unique_results
```

#### Key Design Decisions

**1. Parallel vs Sequential Strategy**
- **Recommendation**: Parallel by default with configurable option
- Rationale: Parallel maximizes information gathering; sequential only needed if quota management critical
- Implementation: Use `asyncio.gather()` for parallel execution

**2. Fallback Chain**
- Tier 1: Fact Check API (professional fact-checkers)
- Tier 2: Google Search (high-quality web sources)
- Tier 3: DuckDuckGo (quota-free fallback)

**3. Error Handling**
- Continue on single-source failure (gather what you can)
- Only fail if ALL sources fail
- Log all failures for debugging

**4. Deduplication Strategy**
- Deduplicate by URL (case-insensitive)
- Keep first occurrence (preserves source priority order)
- Consider normalizing URLs (remove tracking params, fragments)

**5. Metadata Tracking**
- Track which sources were used
- Track quota exceeded events
- Track result counts per source
- Use for monitoring and debugging

**6. Language Fallback Strategy**
- **Configuration**: `DEFAULT_LANGUAGE` and `FALLBACK_LANGUAGE` in settings
- **Logic**: If Fact Check API returns no results in default language, automatically retry with fallback language
- **Use Case**: Hebrew searches fall back to English when Hebrew fact-checks unavailable
- **Tracking**: Add `language_fallback_used` to metadata to monitor fallback usage
- **Example Configuration**:
  ```bash
  DEFAULT_LANGUAGE=he  # Hebrew
  FALLBACK_LANGUAGE=en # English
  ```
- **Benefits**:
  - Better coverage for non-English queries
  - Graceful degradation when local fact-checks unavailable
  - Transparent to user (system handles fallback automatically)

### AH-07: Fact Analyst Node - Tiered Credibility Scoring

**Recommendation**: Implement source credibility weighting system to prioritize professional fact-checkers and authoritative sources

#### Suggested Credibility Scoring System

```python
from urllib.parse import urlparse
from check_it_ai.types.schemas import SearchResult

class SourceCredibilityScorer:
    """Assigns credibility scores to search results based on source type."""

    # Tier 1: Professional fact-checkers (detected by prefix)
    FACT_CHECK_SCORE = 10

    # Tier 2: Authoritative domains
    GOV_EDU_SCORE = 8

    # Tier 3: Reputable news organizations
    NEWS_ORG_SCORE = 6
    NEWS_DOMAINS = {
        "reuters.com", "apnews.com", "bbc.com", "npr.org",
        "theguardian.com", "nytimes.com", "wsj.com"
    }

    # Tier 4: General Google Search results
    GOOGLE_SEARCH_SCORE = 3

    # Tier 5: DuckDuckGo results (lower quality due to no API filtering)
    DUCKDUCKGO_SCORE = 2

    @classmethod
    def score_result(cls, result: SearchResult) -> int:
        """Assign credibility score to a search result.

        Args:
            result: SearchResult to score

        Returns:
            Credibility score (2-10, higher is more credible)
        """
        # Tier 1: Professional fact-checkers
        if "[FACT-CHECK]" in result.title:
            return cls.FACT_CHECK_SCORE

        # Parse domain
        domain = result.display_domain.lower()
        parsed = urlparse(str(result.url))
        netloc = parsed.netloc.lower()

        # Tier 2: Government and educational institutions
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return cls.GOV_EDU_SCORE
        if ".gov." in domain or ".edu." in domain:
            return cls.GOV_EDU_SCORE

        # Tier 3: Reputable news organizations
        for news_domain in cls.NEWS_DOMAINS:
            if news_domain in domain or news_domain in netloc:
                return cls.NEWS_ORG_SCORE

        # Tier 4: General Google Search (default for most results)
        # Heuristic: If not from DuckDuckGo, likely from Google
        # (DuckDuckGo results tend to have simpler domain patterns)
        return cls.GOOGLE_SEARCH_SCORE


def fact_analyst_node(state: AgentState) -> AgentState:
    """Analyze evidence and determine verdict using source credibility weighting."""

    # Score all search results
    scored_results = []
    for result in state.search_results:
        score = SourceCredibilityScorer.score_result(result)
        scored_results.append((result, score))

    # Sort by credibility (highest first)
    scored_results.sort(key=lambda x: x[1], reverse=True)

    # Analyze evidence with credibility weighting
    supporting_evidence = []
    refuting_evidence = []

    for result, credibility_score in scored_results:
        # Use LLM to classify evidence stance
        stance = _classify_evidence_stance(state.claim.claim_text, result)

        if stance == "supporting":
            supporting_evidence.append((result, credibility_score))
        elif stance == "refuting":
            refuting_evidence.append((result, credibility_score))

    # Calculate weighted verdict
    verdict = _calculate_weighted_verdict(supporting_evidence, refuting_evidence)

    # IMPORTANT: Trust fact-checkers when available
    fact_checker_verdict = _get_fact_checker_consensus(scored_results)
    if fact_checker_verdict:
        logger.info(
            f"Using fact-checker consensus: {fact_checker_verdict}",
            extra={"num_fact_checks": len([r for r, s in scored_results if s == 10])}
        )
        verdict = fact_checker_verdict

    state.analysis.verdict = verdict
    state.analysis.supporting_evidence = [r for r, _ in supporting_evidence]
    state.analysis.refuting_evidence = [r for r, _ in refuting_evidence]

    return state


def _get_fact_checker_consensus(scored_results: list[tuple[SearchResult, int]]) -> str | None:
    """Extract consensus from professional fact-checkers if available.

    Fact-checker verdicts should override general web evidence when present.
    """
    fact_check_results = [r for r, score in scored_results if score == 10]

    if not fact_check_results:
        return None

    # Extract ratings from snippets
    ratings = []
    for result in fact_check_results:
        snippet = result.snippet.lower()
        if "rating: false" in snippet or "rating: incorrect" in snippet:
            ratings.append("not_supported")
        elif "rating: true" in snippet or "rating: correct" in snippet:
            ratings.append("supported")
        elif "rating: mixture" in snippet or "rating: partly" in snippet:
            ratings.append("partially_supported")

    # Return consensus if majority agrees
    if ratings:
        from collections import Counter
        consensus = Counter(ratings).most_common(1)[0][0]
        agreement_ratio = ratings.count(consensus) / len(ratings)

        if agreement_ratio >= 0.6:  # 60% agreement threshold
            return consensus

    return None


def _calculate_weighted_verdict(
    supporting: list[tuple[SearchResult, int]],
    refuting: list[tuple[SearchResult, int]]
) -> str:
    """Calculate verdict using credibility-weighted evidence.

    Returns:
        One of: "supported", "not_supported", "partially_supported", "unverifiable"
    """
    if not supporting and not refuting:
        return "unverifiable"

    # Calculate weighted scores
    support_score = sum(score for _, score in supporting)
    refute_score = sum(score for _, score in refuting)

    total_score = support_score + refute_score
    if total_score == 0:
        return "unverifiable"

    support_ratio = support_score / total_score

    # Verdict thresholds
    if support_ratio >= 0.7:
        return "supported"
    elif support_ratio <= 0.3:
        return "not_supported"
    else:
        return "partially_supported"
```

#### Key Design Decisions

**1. Tiered Credibility Scores**
- Score 10: Professional fact-checkers (PolitiFact, Snopes, etc.)
- Score 8: Government and educational institutions (.gov, .edu)
- Score 6: Reputable news organizations (Reuters, AP, BBC, etc.)
- Score 3: General Google Search results
- Score 2: DuckDuckGo results

**2. Fact-Checker Override**
- When professional fact-checkers available, their consensus should override general web evidence
- Requires 60% agreement threshold to establish consensus
- Rationale: Fact-checkers are domain experts who have already done the verification work

**3. Weighted Verdict Calculation**
- Sum credibility scores for supporting vs refuting evidence
- Use ratio to determine verdict (>70% = supported, <30% = not_supported, else = partially_supported)
- Returns "unverifiable" if insufficient evidence

**4. News Organization List**
- Maintain curated list of reputable news organizations
- Consider making this configurable via settings
- Periodically review and update list

**5. Domain Parsing**
- Use both `display_domain` field and URL parsing for robustness
- Handle subdomains correctly (.gov.uk, .edu.au, etc.)

---

**End of AH-03 + AH-04 Summary**

All configuration, logging, caching, Google Search, and Fact Check API infrastructure is production-ready and fully tested. Code has been refactored to eliminate duplication and properly separate concerns between search tools (data fetchers) and nodes (orchestrators).

**Test Results**: All 63 tests pass

**Next Steps**:
- AH-05: Implement Router Node
- AH-06: Implement Researcher Node with multi-source strategy (see suggestions above)
- AH-07: Implement Fact Analyst Node with credibility scoring (see suggestions above)

---

## Integration Testing & Test Suite Reorganization
**Date Added**: 2025-12-10
**Status**: ✅ Completed

### Overview
We have hardened the testing infrastructure by establishing a clear separation between **unit tests** (mocked, fast) and **integration tests** (real API calls, slower).

### 1. Test Suite Reorganization
The test suite has been reorganized into two distinct directories:
- **`tests/unit/`**: Contains all mocked unit tests (Google Search, Fact Check, Schemas). These tests are fast, strictly mocked, and safe to run in CI/CD without API keys.
- **`tests/integration/`**: Contains all tests that make REAL API calls. These require `.env` credentials and consume API quota.

**New Structure**:
```
tests/
├── unit/                       # FAST, MOCKED tests
│   ├── test_google_tool.py
│   ├── test_fact_check_api.py
│   ├── test_duckduckgo_search.py
│   └── ...
├── integration/                # REAL API tests
│   ├── test_real_search_apis.py
│   └── README.md
└── conftest.py
```

### 2. Integration Testing System
We created a dedicated integration testing suite to verify end-to-end functionality with real external services.

**Key Features**:
- **Real API Calls**: Verifies that our API clients actually work with Google and DuckDuckGo.
- **Quota Management**: Tests are marked with `@pytest.mark.integration` and skipped by default in unit test runs.
- **Language Support**: Includes specific tests for Hebrew queries (`he` language code) with fallback verification.
- **Robustness**: Flaky tests (like Zero-Result DuckDuckGo queries) have been hardened with fallback queries.
- **Dependencies**: Migrated from `duckduckgo-search` to `ddgs` to resolve runtime warnings and ensure long-term stability.

**Commands**:
```bash
# Run Unit Tests (Fast, Default)
uv run pytest tests/unit/

# Run Integration Tests (Requires API Keys)
uv run pytest tests/integration/ -v -s -m integration
```

### 3. Documentation
- **`TESTING_GUIDE.md`**: Comprehensive guide on how to run both types of tests, manage API keys, and troubleshoot.
- **`tests/integration/README.md`**: detailed instructions specifically for the integration suite.
