from pydantic import BaseModel
from typing import List


class DotnameSchema(BaseModel):
    """
    Represents a single dot name entry used for identifying geographic or administrative units.

    Attributes:
        id (str): The unique dot name identifier (e.g., 'Africa:Senegal:Saint-Louis').
        text (str): A human-readable label or display name for the region (e.g., 'Saint-Louis').
    """
    id: str
    text: str


class DotnamesListSchema(BaseModel):
    """
    A container schema for a list of dot name objects.

    Attributes:
        dot_names (List[DotnameSchema]): A list of dot name entries.
    """
    dot_names: List[DotnameSchema]