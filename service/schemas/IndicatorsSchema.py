from typing import List, Dict
from pydantic import BaseModel

class IndicatorSchema(BaseModel):
    """
    Represents metadata for a single indicator used in the dashboard.

    Attributes:
        id (str): Unique identifier for the indicator (e.g., "net_use").
        text (str): Human-readable display name (e.g., "Net Use Among Children Under 5").
        version (int): Shapefile version number of the indicator dataset.
        admin_levels (List[int]): List of supported admin levels for this indicator (e.g., [1, 2]).
        subgroups (List[str]): Population subgroups applicable to this indicator (e.g., ["under5", "all"]).
        time (Dict[int, List[int]]): A dictionary representing years and months of data available for this indicator.
                                     For example: {2019: [1, 6, 12], 2020: [1,2,3,4,5,6], 2021: []}
    """
    id: str
    text: str
    version: int
    admin_levels: List[int]
    subgroups: List[str]
    time: Dict[int, List[int]]


class IndicatorsListSchema(BaseModel):
    """
    A container schema for a list of indicator metadata entries.

    Attributes:
        indicators (List[IndicatorSchema]): A list of indicator definitions.
    """
    indicators: List[IndicatorSchema]