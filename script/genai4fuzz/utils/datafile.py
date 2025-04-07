from pathlib import Path
import sys

def find_project_root():
    """Find the root of the Poetry project by looking for 'pyproject.toml'."""
    current = Path(__file__).resolve().parent
    while current != current.root:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Project root not found. Make sure you're in a Poetry project.")

# Get the root of the Poetry project
PROJECT_ROOT = find_project_root()

# Ensure the project root is in sys.path for module imports
sys.path.insert(0, str(PROJECT_ROOT))

def load_data_file(relative_path: str) -> str:
    file_path = PROJECT_ROOT / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return file_path
