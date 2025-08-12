from pydantic import BaseModel, RootModel
from typing import List

class EventsSchema(BaseModel):
    """
    Represents a single time-bound event, such as a holiday or intervention.

    Attributes:
        event (str): Name or label for the event (e.g., "Grand Magal de Touba 2020").
        start_date (str): Start date of the event in YYYY-MM-DD format.
        end_date (str): End date of the event in YYYY-MM-DD format.
    """
    event: str
    start_date: str
    end_date: str


class EventsListSchema(RootModel[List[EventsSchema]]):
    """
    A list of time-bound events returned by the events endpoint.
    """