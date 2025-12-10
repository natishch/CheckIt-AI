import pytest
from pathlib import Path

def pytest_collection_modifyitems(items):
    """Automatically mark all tests in this directory as unit tests."""
    current_dir = Path(__file__).parent
    for item in items:
        # Only mark items that are inside this directory
        item_path = Path(item.fspath)
        if current_dir in item_path.parents:
            item.add_marker(pytest.mark.unit)
