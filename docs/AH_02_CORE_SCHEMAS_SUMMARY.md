# AH-02: Core Schemas & Shared State - Implementation Summary

**Task**: Implement Core Pydantic Models and Shared LangGraph State
**Date**: 2025-12-06
**Status**: ✅ Completed
**Branch**: ah-02-core-schemas-shared-langgraph-state-pydantic

---

## Overview

This task implemented the foundational data models and state management for the check-it-ai fact-checking system. All schemas use strict Pydantic v2 validation to ensure type safety and data integrity throughout the LangGraph workflow.

## What Was Implemented

### 1. Core Schemas (`src/check_it_ai/types/schemas.py`)

Created 7 Pydantic models that define the data structures for the entire fact-checking pipeline:

#### SearchQuery
- **Purpose**: Represents a search query sent to Google Custom Search API
- **Fields**:
  - `query` (str): The search query string (min_length=1)
  - `max_results` (int): Maximum results to return (default=10, range: 1-100)

#### SearchResult
- **Purpose**: Structured response from Google Custom Search API
- **Fields**:
  - `title` (str): Title of the search result
  - `snippet` (str): Preview text snippet
  - `url` (HttpUrl): Validated HTTP/HTTPS URL
  - `display_domain` (str): Domain name for display (e.g., "wikipedia.org")
  - `rank` (int): Position in search results (≥1)
- **Validation**: URL must be valid HTTP/HTTPS, rank must be positive

#### EvidenceItem
- **Purpose**: Individual piece of evidence with citation ID
- **Fields**:
  - `id` (str): Evidence ID in format "E1", "E2", etc.
  - `title` (str): Source title
  - `snippet` (str): Relevant text snippet
  - `url` (HttpUrl): Source URL
  - `display_domain` (str): Domain for display
- **Critical Validator**: `evidence_id` must match regex `^E\d+$`
  - ✅ Valid: "E1", "E2", "E123"
  - ❌ Invalid: "1", "E-1", "e1", "E"

#### Finding
- **Purpose**: A claim with its verdict and supporting evidence
- **Fields**:
  - `claim` (str): The claim being evaluated
  - `verdict` (Literal): One of ["supported", "not_supported", "contested", "insufficient"]
  - `evidence_ids` (list[str]): List of evidence IDs (all validated with `^E\d+$`)
- **Validation**: All evidence_ids must match the evidence ID format

#### EvidenceBundle
- **Purpose**: Complete evidence package for a fact-check
- **Fields**:
  - `items` (list[EvidenceItem]): All evidence items
  - `findings` (list[Finding]): All findings with verdicts
  - `overall_verdict` (Literal): Overall verdict (default="insufficient")
- **Use Case**: Passed from Fact Analyst node to Writer node

#### Citation
- **Purpose**: Links an evidence ID to its source URL
- **Fields**:
  - `evidence_id` (str): Evidence ID being cited (validated with `^E\d+$`)
  - `url` (HttpUrl): URL of the cited source
- **Use Case**: Used in final output to show which sources were cited

#### FinalOutput
- **Purpose**: Final structured output from the Writer node
- **Fields**:
  - `answer` (str): The final answer text
  - `citations` (list[Citation]): All citations used
  - `confidence` (float): Confidence score (range: 0.0 to 1.0)
  - `notes` (str): Additional notes or limitations (default="")
- **Critical Validator**: `confidence` must be between 0.0 and 1.0
  - ✅ Valid: 0.0, 0.5, 0.95, 1.0
  - ❌ Invalid: -0.1, 1.5, 2.0

### 2. LangGraph State (`src/check_it_ai/graph/state.py`)

#### AgentState
- **Purpose**: Shared state passed through all LangGraph nodes
- **Architecture**: Pydantic v2 model with modern ConfigDict
- **Configuration**: `arbitrary_types_allowed=True` for LangGraph compatibility

**State Fields by Phase**:

1. **User Input Phase**:
   - `user_query` (str): Original user question

2. **Router Phase**:
   - `route` (Literal["fact_check", "clarify", "out_of_scope"]): Routing decision

3. **Search Phase**:
   - `search_queries` (list[SearchQuery]): Generated search queries
   - `search_results` (list[SearchResult]): Raw Google API results

4. **Analysis Phase**:
   - `evidence_bundle` (EvidenceBundle | None): Processed evidence from Fact Analyst

5. **Output Phase**:
   - `final_answer` (str): Final generated answer
   - `citations` (list[Citation]): Citations used in answer
   - `confidence` (float): Confidence score (0.0-1.0)

6. **Metadata**:
   - `run_metadata` (dict): Runtime info (latency, token usage, API quota)

**Design Pattern**: Each node receives the full state and returns a state delta (partial update), following LangGraph's functional programming model.

### 3. Comprehensive Test Suite (`tests/test_schemas_validation.py`)

Created **28 unit tests** organized into test classes:

#### TestSearchQuery (3 tests)
- Valid query creation with defaults
- Custom max_results
- Empty string rejection

#### TestSearchResult (3 tests)
- Valid result creation
- Invalid URL rejection
- Rank must be ≥1

#### TestEvidenceItem (7 tests)
- Valid ID formats: "E1", "E123"
- Invalid ID rejection: "1", "E-1", "e1", "E"
- URL validation

#### TestFinding (3 tests)
- Valid finding with evidence IDs
- Invalid evidence ID in list rejection
- Empty evidence list handling

#### TestEvidenceBundle (2 tests)
- Valid bundle creation
- Default verdict behavior

#### TestCitation (3 tests)
- Valid citation creation
- Invalid evidence ID rejection
- Invalid URL rejection

#### TestFinalOutput (7 tests)
- Valid output creation
- Confidence bounds: 0.0 and 1.0 accepted
- Confidence validation: rejects -0.1, 1.5, 2.0
- Default notes behavior

## Key Technical Decisions

### 1. Evidence ID Format: `^E\d+$`
**Rationale**: Simple, unambiguous format for citations
- Easy to parse in UI (e.g., "[E1]", "[E2]")
- Clear distinction from plain numbers
- Supports unlimited evidence items (E1, E2, ..., E999)

### 2. Pydantic v2 with Modern ConfigDict
**Rationale**: Follow Pydantic v2 best practices
- Removed deprecation warnings
- Better IDE support and type checking
- Future-proof for Pydantic v3

### 3. HttpUrl for All URLs
**Rationale**: Automatic validation and security
- Prevents invalid URLs from entering the system
- Ensures http/https protocol
- Catches typos and malformed URLs early

### 4. Confidence as Float (0.0-1.0)
**Rationale**: Standard ML/AI convention
- Easy to interpret as percentage (0.95 = 95% confident)
- Supports fine-grained uncertainty
- Validation prevents out-of-range values

### 5. Literal Types for Verdicts and Routes
**Rationale**: Type safety and IDE autocomplete
- Prevents typos ("suported" vs "supported")
- Clear enumeration of valid values
- Better error messages

## Validation Strategy

### Field-Level Validators
- `@field_validator` for evidence_id format checking
- Pydantic's built-in validators (HttpUrl, ge, le, min_length)
- Custom regex validation for evidence IDs

### Why Strict Validation Matters
1. **Demo Reliability**: Prevents runtime failures during presentations
2. **Debugging**: Clear error messages when invalid data is detected
3. **Type Safety**: Catches bugs at development time, not production
4. **Grading**: Fewer hidden failures = better evaluation

## How to Use These Schemas

### Example: Creating Search Results
```python
from check_it_ai.types.schemas import SearchResult

result = SearchResult(
    title="World War II - Wikipedia",
    snippet="World War II ended in 1945...",
    url="https://en.wikipedia.org/wiki/World_War_II",
    display_domain="en.wikipedia.org",
    rank=1
)
```

### Example: Building Evidence Bundle
```python
from check_it_ai.types.schemas import EvidenceItem, Finding, EvidenceBundle

items = [
    EvidenceItem(
        id="E1",
        title="Wikipedia",
        snippet="WWII ended in 1945",
        url="https://wikipedia.org/wwii",
        display_domain="wikipedia.org"
    )
]

findings = [
    Finding(
        claim="World War II ended in 1945",
        verdict="supported",
        evidence_ids=["E1"]
    )
]

bundle = EvidenceBundle(
    items=items,
    findings=findings,
    overall_verdict="supported"
)
```

### Example: Using AgentState in LangGraph Node
```python
from check_it_ai.graph.state import AgentState

def router_node(state: AgentState) -> AgentState:
    """Router node implementation."""
    # Access current state
    query = state.user_query

    # Make routing decision
    if "history" in query.lower():
        route = "fact_check"
    else:
        route = "out_of_scope"

    # Return state delta (only changed fields)
    return AgentState(route=route)
```

## Testing Strategy

### Run All Schema Tests
```bash
uv run pytest tests/test_schemas_validation.py -v
```

### Run Specific Test Class
```bash
uv run pytest tests/test_schemas_validation.py::TestEvidenceItem -v
```

### Test Coverage
- ✅ Happy path (valid data)
- ✅ Boundary conditions (0.0, 1.0, min/max values)
- ✅ Invalid inputs (wrong format, out of range)
- ✅ Default values and optional fields
- ✅ Edge cases (empty strings, empty lists)

## Integration Points

### Where These Schemas Are Used

1. **Router Node** (`graph/nodes/router.py`)
   - Reads: `state.user_query`
   - Writes: `state.route`

2. **Researcher Node** (`graph/nodes/researcher.py`)
   - Reads: `state.user_query`, `state.route`
   - Writes: `state.search_queries`, `state.search_results`
   - Uses: `SearchQuery`, `SearchResult`

3. **Fact Analyst Node** (`graph/nodes/fact_analyst.py`)
   - Reads: `state.search_results`
   - Writes: `state.evidence_bundle`
   - Uses: `EvidenceItem`, `Finding`, `EvidenceBundle`

4. **Writer Node** (`graph/nodes/writer.py`)
   - Reads: `state.evidence_bundle`
   - Writes: `state.final_answer`, `state.citations`, `state.confidence`
   - Uses: `Citation`, `FinalOutput`

5. **Streamlit UI** (`app/streamlit_app.py`)
   - Displays: `state.final_answer`, `state.citations`, `state.confidence`
   - Shows: `state.evidence_bundle` in evidence panel

## Common Patterns

### Pattern 1: Validating Evidence IDs
```python
# Good: Use the validator
from check_it_ai.types.schemas import EvidenceItem

try:
    item = EvidenceItem(id="E1", ...)  # Validates automatically
except ValidationError:
    # Handle invalid ID
    pass
```

### Pattern 2: Building State Deltas
```python
# Good: Return only changed fields
def my_node(state: AgentState) -> AgentState:
    return AgentState(final_answer="...", confidence=0.95)

# Bad: Don't reconstruct entire state
def my_node(state: AgentState) -> AgentState:
    return AgentState(
        user_query=state.user_query,  # Unnecessary
        route=state.route,            # Unnecessary
        final_answer="...",           # Only this changed
        confidence=0.95               # Only this changed
    )
```

### Pattern 3: Type Hints in Nodes
```python
from check_it_ai.graph.state import AgentState
from check_it_ai.types.schemas import EvidenceBundle

def fact_analyst(state: AgentState) -> AgentState:
    # Type checker knows state.search_results is list[SearchResult]
    results = state.search_results

    # Build evidence bundle
    bundle = EvidenceBundle(...)

    # Return delta
    return AgentState(evidence_bundle=bundle)
```

## Files Modified/Created

### Created
- ✅ `src/check_it_ai/types/schemas.py` (105 lines)
- ✅ `tests/test_schemas_validation.py` (283 lines)
- ✅ `docs/AH_02_CORE_SCHEMAS_SUMMARY.md` (this file)

### Modified
- ✅ `src/check_it_ai/graph/state.py` (60 lines, full rewrite)

## Verification Checklist

- ✅ All 28 schema validation tests pass
- ✅ All 33 total tests pass (including smoke tests)
- ✅ Ruff linting passes with no errors
- ✅ No Pydantic deprecation warnings
- ✅ Import ordering follows project standards
- ✅ Type hints complete and accurate
- ✅ Docstrings on all classes
- ✅ Evidence ID validator works correctly
- ✅ Confidence range validator works correctly
- ✅ URL validation works correctly
- ✅ LangGraph compatibility confirmed

## Next Steps for Future Developers

### AH-03: Implement Graph Nodes
With schemas in place, you can now:
1. Implement `router.py` using `state.user_query` → `state.route`
2. Implement `researcher.py` using `SearchQuery` and `SearchResult`
3. Implement `fact_analyst.py` building `EvidenceBundle`
4. Implement `writer.py` using `Citation` and `FinalOutput`

### AH-04: Google Search Integration
- Use `SearchQuery` to structure API requests
- Parse API responses into `SearchResult` objects
- Store in `state.search_results`

### AH-05: Streamlit UI
- Display `state.final_answer`
- Show `state.citations` as clickable links
- Visualize `state.confidence` as progress bar
- Show `state.evidence_bundle` in expandable panel

## Troubleshooting

### Issue: ValidationError for Evidence ID
**Symptom**: `Evidence ID must match pattern 'E<number>'`
**Solution**: Ensure IDs are uppercase "E" followed by digits: "E1", "E2", etc.

### Issue: ValidationError for Confidence
**Symptom**: `Input should be less than or equal to 1`
**Solution**: Confidence must be between 0.0 and 1.0, not a percentage (use 0.95, not 95)

### Issue: ValidationError for URL
**Symptom**: `Input should be a valid URL`
**Solution**: Ensure URLs include protocol (https://example.com, not example.com)

### Issue: Pydantic Deprecation Warning
**Symptom**: Warning about class-based `config`
**Solution**: Already fixed - we use `model_config = ConfigDict(...)`

## References

- **Technical Design**: `docs/technical_design.pdf` (Section 3.1, 5)
- **Initialization Summary**: `docs/INITIALIZATION_SUMMARY.md`
- **Pydantic Docs**: https://docs.pydantic.dev/latest/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/

## Questions for Next Developer

If you're continuing this work, consider:
1. Should we add a `source_credibility_score` field to `EvidenceItem`?
2. Do we need a `timestamp` field in `run_metadata`?
3. Should `EvidenceBundle` validate that all `evidence_ids` in findings exist in items?
4. Should we add a `SearchResultMetadata` model for API quota info?

---

**End of AH-02 Summary**
All core schemas are production-ready and fully tested. Next task: AH-03 (Graph Nodes Implementation).
