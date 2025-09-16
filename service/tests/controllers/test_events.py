from unittest.mock import patch
import pandas as pd
from tests.conftest import client


def test_get_events_success(client):
    '''
    Test successful fetch of events
    '''
    # Mock pd.read_csv to return valid data
    df_mock = pd.DataFrame([
        {'event': 'Test Event 1', 'start_date': '2021-01-01', 'end_date': '2021-01-02'},
        {'event': 'Test Event 2', 'start_date': '2021-02-01', 'end_date': '2021-02-02'},
    ])

    with patch('service.controllers.events.pd.read_csv', return_value=df_mock):
        response = client.get("/events/")
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["event"] == "Test Event 1"


def test_get_events_file_not_found(client):
    '''
    Test events file missing
    '''
    df_mock = "events.csv not found"

    with patch('service.controllers.events.pd.read_csv', return_value=df_mock):
        response = client.get("/events/")
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


def test_get_events_missing_columns(client):
    '''
    Test missing CSV col
    '''
    df_mock = pd.DataFrame([
        {'event': 'Event X', 'start_date': '2021-01-01'}
    ])

    with patch('service.controllers.events.pd.read_csv', return_value=df_mock):
        response = client.get("/events/")
        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


def test_get_events_duplicate_entries(client):
    '''
    Test duplicate events
    '''
    df_mock = pd.DataFrame([
        {'event': 'Duplicate Event', 'start_date': '2021-01-01', 'end_date': '2021-01-02'},
        {'event': 'Duplicate Event', 'start_date': '2021-02-01', 'end_date': '2021-02-02'},
    ])

    with patch('service.controllers.events.pd.read_csv', return_value=df_mock):
        response = client.get("/events/")
        assert response.status_code == 200
        # Second duplicate will overwrite first in dict, so only one will survive
        assert len(response.json()) == 1