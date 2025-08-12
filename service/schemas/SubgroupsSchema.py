from pydantic import BaseModel
from typing import List

class SubgroupSchema(BaseModel):
    """
    Represents a single population subgroup associated with an indicator.

    Attributes:
        id (str): Unique identifier for the subgroup (e.g., "under5", "pregnant_women").
        text (str): Human-readable display name for the subgroup (e.g., "Children Under 5").
    """
    id: str
    text: str


class SubgroupsListSchema(BaseModel):
    """
    A container schema for a list of subgroups available for a given indicator.

    Attributes:
        subgroups (List[SubgroupSchema]): A list of defined population subgroups.
    """
    subgroups: List[SubgroupSchema]
