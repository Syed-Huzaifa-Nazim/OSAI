"""Pydantic request/response models.

These mirror the TypeScript types in ``frontend/src/types/`` one-for-one. When
one side changes, change the other in the same commit.
"""

from app.models.common import CamelModel  # noqa: F401
