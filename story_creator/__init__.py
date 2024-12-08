# story_creator/__init__.py

"""
Story Creator Package Initialization.

This module imports key classes and functions from submodules
and initializes the database by creating tables if they don't exist.
"""

from .new_models import (
    Base,
    # Other models...
)
from .database import engine

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
