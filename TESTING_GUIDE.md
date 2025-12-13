# Testing Guide for Check-It AI

This guide explains how to test the search functionality with both mocked tests (fast, no API usage) and real integration tests (actual API calls).

## Quick Start

### 1. Run Fast Unit Tests (Mocked, No API Keys Needed)

```bash
# Run all unit tests (default, fast)
uv run pytest -m unit

# Or explicitly skip integration tests
uv run pytest tests/ --ignore=tests/integration/
```

These tests use mocks and don't make real API calls. They're fast and don't use API quota.

**Result:** All 104 unit tests should pass ✅

---

### 2. Test Real APIs (Requires API Credentials)

#### Step 1: Get API Credentials

**Google API Key** (required for Google Search & Fact Check API):
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project
3. Enable these APIs:
   - Custom Search API
   - Fact Check Tools API (optional)
4. Create API key in "Credentials"

**Custom Search Engine ID** (required for Google Search):
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" to create new search engine
3. Select "Search the entire web"
4. Copy the "Search engine ID"

#### Step 2: Configure `.env`

```bash
# Create .env from example
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Required for Google Search
GOOGLE_API_KEY=AIza...your_actual_key_here
GOOGLE_CSE_ID=a1b2c3d4e5...your_cse_id_here

# Optional: Enable fact-checking
USE_FACT_CHECK_API=true

# Optional: Configure language (for Hebrew support)
DEFAULT_LANGUAGE=he
FALLBACK_LANGUAGE=en
```

#### Step 3: Run Integration Tests

```bash
# Run all integration tests (makes real API calls)
uv run pytest tests/integration/ -v -s -m integration
```

**What happens:**
- Tests make real API calls to Google, Fact Check API, and DuckDuckGo
- You'll see actual search results printed
- Uses your API quota (minimal usage, ~10-20 queries)

---

## Test Types

### Unit Tests (Default)
- **Location:** `tests/unit/` and `tests/graph/`
- **Speed:** Fast (~0.5s for 104 tests)
- **API Calls:** None (uses mocks)
- **API Keys:** Not required
- **Quota Usage:** Zero
- **Run:** `uv run pytest -m unit`

### Integration Tests
- **Location:** `tests/integration/`
- **Speed:** Slower (~5-10s depending on network)
- **API Calls:** Real API calls
- **API Keys:** Required (except DuckDuckGo)
- **Quota Usage:** ~2-5 queries per test
- **Run:** `uv run pytest tests/integration/ -v -s -m integration`

### E2E Tests (Router → Researcher Flow)
- **Location:** `tests/e2e/`
- **Speed:** Slower (~5-10s depending on network)
- **API Calls:** Real API calls (Google Search)
- **API Keys:** Required
- **Quota Usage:** ~5-10 queries per test
- **Run:** `uv run pytest tests/e2e/ -v -s`
- **Tests:** Router classification → Researcher query expansion → Search execution

---

## Running Specific Tests

### Test Individual Search Providers

```bash
# Test Google Search only
uv run pytest tests/integration/test_real_search_apis.py::TestRealGoogleSearch -v -s

# Test Fact Check API only
uv run pytest tests/integration/test_real_search_apis.py::TestRealFactCheckAPI -v -s

# Test DuckDuckGo only (no API key needed!)
uv run pytest tests/integration/test_real_search_apis.py::TestRealDuckDuckGoSearch -v -s

# Test multi-source workflow
uv run pytest tests/integration/test_real_search_apis.py::TestMultiSourceWorkflow -v -s
```

### Test Specific Features

```bash
# Test Hebrew query support
uv run pytest tests/integration/ -k "hebrew" -v -s

# Test language fallback feature
uv run pytest tests/integration/ -k "fallback" -v -s
```

---

## Expected Output

### Unit Tests (Mocked)
```
============================== 63 passed in 0.08s ==============================
```

### Integration Tests (Real APIs)

#### If Credentials Not Configured:
```
SKIPPED [1] test_real_search_apis.py::...: Google API credentials not configured
```
This is **expected** - tests gracefully skip when credentials missing.

#### If Credentials Configured:
```
✅ Google Search Results for 'Python programming language':
  [1] Python (programming language) - Wikipedia
      https://en.wikipedia.org/wiki/Python_(programming_language)
      Python is a high-level, general-purpose programming language...

✅ Fact Check API Results for 'COVID-19 vaccine safety':
  [1] [FACT-CHECK] COVID-19 vaccines are safe and effective
      https://www.politifact.com/...
      Rating: True | Multiple studies confirm...

============================== 4 passed in 3.21s ===============================
```

---

## Testing Language Fallback (Hebrew → English)

This is critical for your use case! Test it with:

```bash
# Test Hebrew search with English fallback
uv run pytest tests/integration/test_real_search_apis.py::TestRealFactCheckAPI::test_fact_check_api_hebrew_with_fallback -v -s
```

**Expected behavior:**
1. Searches for Hebrew fact-checks first (`language_code="he"`)
2. If no results, automatically falls back to English (`language_code="en"`)
3. Returns English fact-checks when Hebrew unavailable

**Example output:**
```
✅ Fact Check API Results for Hebrew query 'חיסון קורונה':
   Hebrew results: 0
   ⚠️  No Hebrew fact-checks, trying English fallback...
   English results: 3
   ✅ Fallback successful! Got English fact-checks:
      [1] [FACT-CHECK] COVID-19 vaccines are safe
```

---

## API Quota Management

### Free Tier Limits
- **Google Custom Search:** 100 queries/day (free)
- **Fact Check Tools:** 100 queries/day (shares quota with Custom Search)
- **DuckDuckGo:** No quota limits (free)

### Quota Usage Per Test Run
- **Unit tests:** 0 queries (uses mocks)
- **Integration tests (all):** ~10-15 queries
- **Integration tests (specific):** ~2-5 queries

### Caching Saves Quota
The system automatically caches results for 24 hours (configurable). If you run the same test twice within 24 hours, the second run uses cache instead of making API calls.

**Check cache:**
```bash
ls -la cache/
```

**Clear cache** (forces fresh API calls):
```bash
rm -rf cache/*.json
```

---

## Troubleshooting

### "Google API credentials not configured"
**Solution:** Add credentials to `.env` file (see Step 2 above)

### "API quota exceeded"
**Solutions:**
- Wait until tomorrow (quota resets daily)
- Upgrade to paid tier ($5 per 1,000 queries after free tier)
- Use caching (already enabled by default)
- Run fewer tests

### "No fact-check results found"
**This is normal!** The Fact Check API doesn't have fact-checks for every topic.

Try these known fact-checked topics:
- "COVID-19 vaccine safety"
- "climate change evidence"
- "2020 election results"
- "moon landing hoax"

### "DuckDuckGo search failed"
**Solutions:**
- Check internet connection
- Wait a few seconds (rate limiting)
- DuckDuckGo occasionally blocks automated requests temporarily (using `ddgs` library)

---

## Best Practices

### For Development (Daily Work)
✅ Run unit tests: `uv run pytest -m unit`
- Fast, no API usage
- Comprehensive coverage
- Safe to run frequently

### Before Committing Code
✅ Run unit tests: `uv run pytest -m unit`
✅ Check linting: `uv run ruff check src/ tests/`

### For Feature Verification
✅ Run specific integration test:
```bash
uv run pytest tests/integration/ -k "test_name" -v -s
```

### For Full System Validation
✅ Run all tests once:
```bash
# Unit tests
uv run pytest -m unit

# Integration tests (uses API quota)
uv run pytest tests/integration/ -v -s
```

---

## CI/CD Considerations

For CI/CD pipelines, **only run unit tests** to avoid API quota usage:

```yaml
# GitHub Actions example
- name: Run tests
  run: uv run pytest -m unit
```

Run integration tests **manually** or on a **schedule** (e.g., nightly) with credentials stored as secrets.

---

## Summary

| Test Type | Command | Speed | API Calls | When to Use |
|-----------|---------|-------|-----------|-------------|
| **Unit Tests** | `uv run pytest -m unit` | Fast | No | Daily development |
| **Integration Tests** | `uv run pytest tests/integration/ -v -s` | Slow | Yes | Feature verification |
| **E2E Tests** | `uv run pytest tests/e2e/ -v -s` | Slow | Yes | Router → Researcher flow |
| **Specific Feature** | `uv run pytest tests/integration/ -k "keyword"` | Medium | Yes | Testing specific functionality |
| **Hebrew Fallback** | `uv run pytest -k "hebrew"` | Medium | Yes | Language support validation |

---

**Need help?** Check [tests/integration/README.md](tests/integration/README.md) for detailed integration testing guide.
