"""Streamlit Chat UI for Check-It AI fact verification system."""


import httpx
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Check-It AI", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    /* Main title styling */
    .main-title {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Evidence card styling */
    .evidence-card {
        background: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 4px;
    }

    .evidence-url {
        color: #1f77b4;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# API Configuration
API_BASE_URL = "http://localhost:8000"


def check_claim(claim_text: str) -> dict | None:
    """Call the Check-It AI API to verify a claim."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE_URL}/api/check", json={"text": claim_text})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"API Error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None


def get_verdict_emoji(answer: str) -> str:
    """Determine verdict emoji based on answer content."""
    answer_lower = answer.lower()
    if any(
        word in answer_lower for word in ["true", "confirm", "correct", "accurate", "consensus"]
    ):
        return "✅"
    elif any(word in answer_lower for word in ["false", "debunk", "incorrect", "inaccurate"]):
        return "❌"
    else:
        return "⚠️"


def render_evidence_card(citation: dict, index: int):
    """Render an evidence card for a citation."""
    evidence_id = citation.get("evidence_id", "N/A")
    url = citation.get("url", "#")

    # Extract domain from URL
    try:
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
    except Exception:
        domain = url

    st.markdown(
        f"""
    <div class="evidence-card">
        <div style="font-weight: bold; color: #333;">📄 Source {index + 1} ({evidence_id})</div>
        <div class="evidence-url">🔗 <a href="{url}" target="_blank">{domain}</a></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_confidence_meter(confidence: float):
    """Render a visual confidence meter."""
    percentage = int(confidence * 100)

    # Determine color based on confidence
    if confidence >= 0.8:
        color = "#28a745"  # Green
    elif confidence >= 0.5:
        color = "#ffc107"  # Yellow
    else:
        color = "#dc3545"  # Red

    st.markdown(
        f"""
    <div style="margin: 1rem 0;">
        <strong>Confidence Level:</strong> {percentage}%
        <div style="background: #e9ecef; border-radius: 10px; height: 20px; margin-top: 0.5rem;">
            <div style="background: {color}; width: {percentage}%; height: 100%; border-radius: 10px;"></div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Header
st.markdown('<h1 class="main-title">🔍 Check-It AI</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">AI-Powered Fact Verification Assistant</p>', unsafe_allow_html=True
)

# Example claims (shown only if no messages yet)
if not st.session_state.messages:
    st.markdown("### Try these example claims:")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🌍 The Earth is round", key="ex1"):
            st.session_state.example_claim = "The Earth is round"
            st.rerun()

    with col2:
        if st.button("💉 Vaccines cause autism", key="ex2"):
            st.session_state.example_claim = "Vaccines cause autism"
            st.rerun()

    with col3:
        if st.button("🌡️ Climate change is real", key="ex3"):
            st.session_state.example_claim = "Climate change is real"
            st.rerun()

    st.divider()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            # Assistant message with structured response
            response_data = message["content"]

            # Display verdict with emoji
            verdict_emoji = get_verdict_emoji(response_data["answer"])
            st.markdown(f"### {verdict_emoji} Verdict")
            st.write(response_data["answer"])

            # Display confidence meter
            render_confidence_meter(response_data["confidence"])

            # Display citations
            if response_data.get("citations"):
                st.markdown("### 📚 Evidence Sources")
                for idx, citation in enumerate(response_data["citations"]):
                    render_evidence_card(citation, idx)

            # Display notes if available
            if response_data.get("notes"):
                with st.expander("📝 Additional Notes"):
                    st.info(response_data["notes"])

# Handle example claim selection
if "example_claim" in st.session_state:
    user_input = st.session_state.example_claim
    del st.session_state.example_claim
else:
    # Chat input
    user_input = st.chat_input("Enter a claim to verify...")

# Process user input
if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user"):
        st.write(user_input)

    # Display assistant response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Analyzing claim..."):
            # Call API
            response = check_claim(user_input)

            if response:
                # Store response in session state
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Display verdict
                verdict_emoji = get_verdict_emoji(response["answer"])
                st.markdown(f"### {verdict_emoji} Verdict")
                st.write(response["answer"])

                # Display confidence
                render_confidence_meter(response["confidence"])

                # Display citations
                if response.get("citations"):
                    st.markdown("### 📚 Evidence Sources")
                    for idx, citation in enumerate(response["citations"]):
                        render_evidence_card(citation, idx)

                # Display notes
                if response.get("notes"):
                    with st.expander("📝 Additional Notes"):
                        st.info(response["notes"])
            else:
                st.error(
                    "Failed to get response from API. Make sure the backend server is running on http://localhost:8000"
                )

# Sidebar
with st.sidebar:
    st.markdown("## About")
    st.info("""
    **Check-It AI** uses multiple sources to verify claims:

    - 🔍 Google Search
    - ✅ Fact-Check APIs
    - 🦆 DuckDuckGo (fallback)

    The AI analyzes evidence and provides a verdict with confidence scoring.
    """)

    st.divider()

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    # Stats
    st.markdown("### 📊 Session Stats")
    num_claims = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("Claims Checked", num_claims)
