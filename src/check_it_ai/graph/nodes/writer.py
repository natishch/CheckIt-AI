"""Writer node using fine-tuned LoRA model."""


def write_response(state: dict) -> dict:
    """Generate final evidence-grounded response."""
    return {"final_answer": "Placeholder answer"}
