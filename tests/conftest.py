import pytest
import logging

# Configure pytest to show live logs
def pytest_configure():
    """Configure pytest to show live logs during test execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Set up logging for all tests."""
    caplog.set_level(logging.INFO)
    return caplog
