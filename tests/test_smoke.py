"""Smoke tests to verify package structure and imports."""


def test_import_main_package():
    """Test that the main package can be imported."""
    import check_it_ai

    assert check_it_ai is not None


def test_import_config():
    """Test that config module can be imported."""
    from check_it_ai import config

    assert config is not None


def test_import_graph():
    """Test that graph module can be imported."""
    from check_it_ai.graph import graph

    assert graph is not None


def test_import_state():
    """Test that state module can be imported."""
    from check_it_ai.graph import state

    assert state is not None


def test_run_graph_function():
    """Test that run_graph function exists and is callable."""
    from check_it_ai.graph.graph import run_graph

    result = run_graph("test query")
    assert isinstance(result, dict)
    assert "final_answer" in result
