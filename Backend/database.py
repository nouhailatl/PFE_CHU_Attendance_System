"""Compatibility wrapper for the database package.

Runtime code can keep importing `database` while the actual implementation
lives in `Backend/db/database.py`.
"""

from db.database import *  # noqa: F403
