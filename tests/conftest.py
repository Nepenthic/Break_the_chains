import os
import sys
import pytest

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the project root to the Python path
sys.path.insert(0, project_root)

# Add any shared fixtures here if needed
@pytest.fixture(scope="session")
def project_root_path():
    return project_root 