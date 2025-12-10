
NON_HISTORICAL_HINTS: dict[str, tuple[str, ...]] = {
    "creative_request": (
        "write me a poem",
        "poem about",
        "song about",
        "lyrics about",
        "short story",
        "story about",
        "screenplay",
        "script for",
    ),
    "coding_request": (
        "python code",
        "python script",
        "write a python script",
        "write code",
        "code this",
        "bash script",
        "shell script",
        "powershell script",
        "dockerfile",
        "docker compose",
        "sql query",
        "regex for",
    ),
    "chat_request": (
        "tell me a joke",
        "make me laugh",
        "roast me",
        "pick up line",
        "pickup line",
        "dating advice",
        "relationship advice",
        "life advice",
    ),
}


# Light-weight historical keywords (optional, mostly for metadata)
HISTORICAL_KEYWORDS = (
    "war",
    "revolution",
    "empire",
    "king",
    "queen",
    "president",
    "treaty",
    "independence",
    "invasion",
    "dynasty",
    "civil rights",
    "kingdom",
    "empire",
    "roman",
    "medieval",
    "ancient",
)

# More robust non-historical hints
CREATIVE_HINTS = (
    "write a poem",
    "write me a poem",
    "poem about",
    "song about",
    "lyrics about",
    "rap about",
    "story about",
    "short story",
    "novel about",
    "fanfic",
    "fan fiction",
    "script for",
    "screenplay",
    "youtube script",
    "tiktok script",
    "instagram post",
    "tweet about",
    "facebook post",
    "linkedin post",
)

CODING_HINTS = (
    "python code",
    "python function",
    "in python",
    "in java",
    "in c++",
    "in c#",
    "in javascript",
    "js code",
    "node.js",
    "write code",
    "code this",
    "write a script",
    "bash script",
    "shell script",
    "powershell script",
    "sql query",
    "regex for",
    "dockerfile",
    "docker compose",
    "api endpoint",
)

GENERIC_CHAT_HINTS = (
    "tell me a joke",
    "make me laugh",
    "roast me",
    "pick-up line",
    "pickup line",
    "relationship advice",
    "dating advice",
    "diet plan",
    "workout plan",
    "life advice",
)

# Very generic questions that are “about truth” but contain no content
GENERIC_TRUTH_QUESTIONS = {
    "did it happen?",
    "is it true?",
    "is that true?",
    "what happened?",
}