"""Shared model base.

Python stays snake_case; the wire format is camelCase, which is what the
frontend types expect. ``populate_by_name`` means either spelling parses, so
tests can construct models with Python names.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
