"""Researcher Node: Query Expansion and Search Execution with Deduplication.

This node implements the Researcher Agent that:
1. Expands user queries into multiple search queries for broader coverage
2. Executes searches using Google Search API
3. Supports trusted domains filtering
4. Deduplicates results by URL (keeps highest-ranked occurrence)
"""

from check_it_ai.config import settings
from check_it_ai.graph.state import AgentState
from check_it_ai.tools.google_search import google_search
from check_it_ai.types.schemas import SearchQuery, SearchResult
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)


def expand_query(user_query: str, trusted_sources_only: bool = False) -> list[str]:
    """Expand a user query into multiple diverse search queries.

    Implements query expansion heuristics to broaden coverage:
    - Original query
    - Query with date/history context
    - Query with verification keywords

    Args:
        user_query: The original user query
        trusted_sources_only: If True, append site filters for trusted domains

    Returns:
        List of up to 3 expanded search queries
    """
    if not user_query or not user_query.strip():
        return []

    user_query = user_query.strip()
    expanded_queries = []

    # Query 1: Original query
    base_query = user_query
    if trusted_sources_only:
        base_query = (
            f"{user_query} site:wikipedia.org OR site:britannica.com OR site:.edu OR site:.gov"
        )
    expanded_queries.append(base_query)

    # Query 2: Add historical context (unless already contains "history")
    if "history" not in user_query.lower() and len(expanded_queries) < 3:
        history_query = f"{user_query} history"
        if trusted_sources_only:
            history_query = f"{user_query} history site:wikipedia.org OR site:britannica.com OR site:.edu OR site:.gov"
        expanded_queries.append(history_query)

    # Query 3: Add verification context (for fact-checking queries)
    if (
        "truth" not in user_query.lower()
        and "fact" not in user_query.lower()
        and len(expanded_queries) < 3
    ):
        verification_query = f"{user_query} facts"
        if trusted_sources_only:
            verification_query = f"{user_query} facts site:wikipedia.org OR site:britannica.com OR site:.edu OR site:.gov"
        expanded_queries.append(verification_query)

    # Ensure we return up to 3 queries
    return expanded_queries[:3]


def deduplicate_by_url(results: list[SearchResult]) -> list[SearchResult]:
    """Deduplicate search results by URL, keeping the highest-ranked (first) occurrence.

    Args:
        results: List of SearchResult objects (may contain duplicates)

    Returns:
        Deduplicated list of SearchResult objects
    """
    seen_urls = set()
    deduplicated = []

    for result in results:
        # Normalize URL to lowercase for case-insensitive comparison
        url_str = str(result.url).lower()

        if url_str not in seen_urls:
            seen_urls.add(url_str)
            deduplicated.append(result)
        else:
            logger.debug(f"Skipping duplicate URL: {result.url}", extra={"title": result.title})

    logger.info(
        f"Deduplication: {len(results)} total results → {len(deduplicated)} unique results",
        extra={"duplicates_removed": len(results) - len(deduplicated)},
    )

    return deduplicated


def researcher_node(state: AgentState) -> dict:
    """Researcher Node: Expands queries, executes searches, and deduplicates results.

    This node:
    1. Expands the user query into up to 3 diverse search queries
    2. Executes Google Search API calls for each query
    3. Checks for TRUSTED_SOURCES_ONLY config flag and appends site filters
    4. Deduplicates results by URL (keeps highest-ranked occurrence)
    5. Updates state with search_queries and search_results

    Args:
        state: Current AgentState with user_query populated

    Returns:
        Updated AgentState with search_queries and search_results
    """
    user_query = state.user_query

    if not user_query or not user_query.strip():
        logger.warning("Empty user query provided to researcher node")
        return {"search_queries": [], "search_results": []}

    logger.info(f"Starting research for query: {user_query}")

    # Check for trusted domains configuration
    # This feature can be enabled via TRUSTED_DOMAINS_ONLY in .env
    trusted_sources_only = settings.trusted_domains_only

    # Step 1: Query Expansion
    expanded_queries = expand_query(user_query, trusted_sources_only=trusted_sources_only)
    logger.info(
        f"Expanded query into {len(expanded_queries)} search queries",
        extra={"original_query": user_query, "expanded_count": len(expanded_queries)},
    )

    # Convert to SearchQuery objects
    search_queries = [
        SearchQuery(query=q, max_results=settings.max_search_results) for q in expanded_queries
    ]

    # Step 2: Execute Searches
    all_results = []
    for i, search_query in enumerate(search_queries, start=1):
        try:
            logger.info(f"Executing search query {i}/{len(search_queries)}: {search_query.query}")
            results = google_search(query=search_query.query, num_results=search_query.max_results)
            all_results.extend(results)
            logger.info(
                f"Retrieved {len(results)} results from query {i}",
                extra={"query": search_query.query, "num_results": len(results)},
            )
        except Exception as e:
            logger.error(
                f"Failed to execute search query {i}: {search_query.query}", extra={"error": str(e)}
            )
            # Continue with other queries even if one fails
            continue

    # Step 3: Deduplicate by URL
    deduplicated_results = deduplicate_by_url(all_results)

    logger.info(
        f"Research complete: {len(deduplicated_results)} unique results from {len(expanded_queries)} queries",
        extra={
            "user_query": user_query,
            "total_results": len(all_results),
            "unique_results": len(deduplicated_results),
            "queries_executed": len(search_queries),
        },
    )

    # Step 4: Update state (return state delta)
    return {"search_queries": search_queries, "search_results": deduplicated_results}
