import pytest
import logging

# Configure pytest to show live logs
# def pytest_configure(): 
#     """Configure pytest to show live logs during test execution."""
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Set up logging level for capture by pytest.
    Note: This primarily affects pytest's internal capture, not direct console output.
    Console output is typically controlled by pytest.ini or the -s flag.
    """
    # Setting the level here ensures caplog captures INFO level messages if needed within tests
    caplog.set_level(logging.INFO)
    return caplog
