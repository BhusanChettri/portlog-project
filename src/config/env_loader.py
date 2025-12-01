"""Centralized environment variable loading utility.

This module provides a single function to load environment variables,
eliminating code duplication across the codebase.
"""

from pathlib import Path
from dotenv import load_dotenv


def load_environment_variables(project_dir: Path = None) -> None:
    """Load environment variables from .env file.
    
    Checks for .env file in parent directory first, then in project directory.
    This matches the pattern used throughout the codebase.
    
    Args:
        project_dir: Project root directory. If None, calculates from calling file.
    """
    if project_dir is None:
        # Default: assume this is called from src/core/*.py
        # Calculate project root (3 levels up from src/core)
        project_dir = Path(__file__).parent.parent.parent
    
    parent_dir = project_dir.parent
    env_file = parent_dir / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
    elif (project_dir / ".env").exists():
        load_dotenv(project_dir / ".env")

