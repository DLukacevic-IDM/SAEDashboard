import os
import pandas as pd
from schemas.EventsSchema import EventsListSchema
from service.helpers.controller_helpers import ControllerException
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/events/", response_model=EventsListSchema)
async def get_events():
    """
    Retrieves a list of historical events with start and end dates.

    This endpoint returns a list of predefined events (e.g., national holidays,
    religious gatherings, or notable occurrences) loaded from a local CSV file called 'events.csv'.
    Each event includes its name, start date, and end date.

    The data is used to support contextual analysis, such as identifying periods
    that may influence mobility, service utilization, or epidemiological patterns.

    Returns:
        List[dict]: A list of event objects with `event`, `start_date`, and `end_date` fields.

    Example 1: /events
    return:
     [
         {
             "event": "Grand Magal de Touba 2020",
             "start_date": "2020-10-05",
             "end_date": "2020-10-06"
         },
         {
             "event": "Grand Magal de Touba 2021",
             "start_date": "2021-09-25",
             "end_date": "2021-09-26"
         },
         {
             "event": "Grand Magal de Touba 2022",
             "start_date": "2022-09-14",
             "end_date": "2022-09-15"
         }
     ]
    """

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(current_dir, '..', 'data', 'events.csv')
        df = pd.read_csv(file)
        data = {}
        for index, row in df.iterrows():
            data[row['event']] = {
                'event': row['event'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
            }

        return list(data.values())

    except ControllerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # re-raise deliberate FastAPI exceptions
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
