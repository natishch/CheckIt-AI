# Integration Tests

Integration tests that make **real API calls** to verify search functionality end-to-end.

## ⚠️ Important Notes

- **These tests use real API quota** - be mindful of rate limits and costs
- **These tests are NOT run by default** in regular test suites
- **API credentials required** for Google Search and Fact Check API tests
- **DuckDuckGo tests work without credentials** (no API key needed)
- **Dependency Update**: Migrated from `duckduckgo-search` to `ddgs` (v1.3.1) for better stability

## Setup

### 1. Configure API Credentials

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add:

```bash
# Required for Google Search and Fact Check API
GOOGLE_API_KEY=your_actual_api_key_here
GOOGLE_CSE_ID=your_actual_cse_id_here

# Optional: Enable/disable features
USE_FACT_CHECK_API=true
DEFAULT_LANGUAGE=he
FALLBACK_LANGUAGE=en
```

### 2. Get Google API Credentials

**Google API Key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable "Custom Search API" and "Fact Check Tools API"
4. Create API key in "Credentials"

**Custom Search Engine ID:**
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Create new search engine (search entire web)
3. Copy the "Search engine ID"

## Running Integration Tests

### Run All Integration Tests

```bash
# Run with verbose output and print statements
uv run pytest tests/integration/ -v -s -m integration
```

### Run Specific Test Classes

```bash
# Test only Google Search
uv run pytest tests/integration/test_real_search_apis.py::TestRealGoogleSearch -v -s

# Test only Fact Check API
uv run pytest tests/integration/test_real_search_apis.py::TestRealFactCheckAPI -v -s

# Test only DuckDuckGo (no credentials needed)
uv run pytest tests/integration/test_real_search_apis.py::TestRealDuckDuckGoSearch -v -s

# Test multi-source workflow
uv run pytest tests/integration/test_real_search_apis.py::TestMultiSourceWorkflow -v -s
```

### Run Specific Tests

```bash
# Test Google Search with English query
uv run pytest tests/integration/test_real_search_apis.py::TestRealGoogleSearch::test_google_search_real_api -v -s

# Test Hebrew search with fallback
uv run pytest tests/integration/test_real_search_apis.py::TestRealFactCheckAPI::test_fact_check_api_hebrew_with_fallback -v -s
```

## Regular Test Suite (Skip Integration Tests)

When running regular unit tests, integration tests are automatically skipped:

```bash
# Run only unit tests (fast, mocked)
uv run pytest tests/ --ignore=tests/integration/

# Or just run regular tests (integration/ is in testpaths but marked)
uv run pytest
```

## Test Coverage

### TestRealGoogleSearch
- ✅ Basic Google Search with English query
- ✅ Google Search with Hebrew query (tests multilingual support)

### TestRealFactCheckAPI
- ✅ Fact Check API with common fact-checked topic
- ✅ Hebrew query with fallback to English (tests language fallback feature)

### TestRealDuckDuckGoSearch
- ✅ DuckDuckGo search (no API key needed)
- ✅ Hebrew query support

### TestMultiSourceWorkflow
- ✅ Multi-source search across all providers
- ✅ Fallback chain validation
- ✅ Result aggregation

## Expected Behavior

### If Credentials Not Configured
Tests will **skip gracefully** with message:
```
SKIPPED [1] Google API credentials not configured
```

### If Quota Exceeded
Tests will **fail** with helpful error message indicating quota exceeded.

### Successful Tests
Will print actual search results for manual verification:
```
✅ Google Search Results for 'Python programming language':
  [1] Python (programming language) - Wikipedia
      https://en.wikipedia.org/wiki/Python_(programming_language)
      Python is a high-level, general-purpose programming language...
```

## Troubleshooting

### "Google API credentials not configured"
- Ensure `.env` file exists
- Check `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` are set correctly

### "API quota exceeded"
- Check your Google Cloud Console quotas
- Consider upgrading to paid tier if testing heavily
- Use caching to reduce API calls (already implemented)

### "No fact-check results found"
- This is **normal** - Fact Check API doesn't have fact-checks for every topic
- Try queries like: "COVID-19 vaccine", "climate change", "election results"

### "DuckDuckGo search failed"
- Check internet connection
- DuckDuckGo rate limits are generous but exist
- Wait a few seconds between tests

## Cost Considerations

**Google Custom Search API:**
- Free tier: 100 queries/day
- Paid tier: $5 per 1,000 queries after free tier
- These integration tests use ~10-20 queries per full run

**Fact Check Tools API:**
- Same quota as Custom Search API
- Uses same API key

**DuckDuckGo:**
- Free, no API key required
- Rate limited but generous for testing

## Best Practices

1. **Run integration tests sparingly** - use unit tests for regular development
2. **Use caching** - already implemented, reduces API calls for repeated queries
3. **Monitor quota usage** - check Google Cloud Console regularly
4. **Test with real queries** - use actual user scenarios
5. **Verify Hebrew support** - critical for your use case
