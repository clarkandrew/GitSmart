import pytest
from GitSmart.main import entry_point

def test_main_runs_without_crashing(monkeypatch):
    """
    Basic smoke test to ensure `main` function can be called
    without raising exceptions.
    """
    try:
        entry_point()
    except SystemExit:
        pass
    except Exception as e:
        pytest.fail(f"main crashed unexpectedly: {e}")
