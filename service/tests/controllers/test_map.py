from unittest.mock import patch
import pandas as pd
from tests.conftest import client


MOCK_DF = pd.DataFrame([
    {
        'dot_name': 'Africa:Benin:Borgou',
        'year': 2007,
        'data': 0.1,
        'data_lower_bound': 0.08,
        'data_upper_bound': 0.12
    },
    {
        'dot_name': 'Africa:Benin:Collines',
        'year': 2007,
        'data': 0.2,
        'data_lower_bound': None,
        'data_upper_bound': None
    }
])

@patch("service.controllers.map.get_dataframe", return_value=MOCK_DF)
@patch("service.controllers.map.get_all_countries", return_value=["Benin"])
def test_map_valid_input(mock_get_all_countries, mock_get_dataframe, client):
    '''
    Tests that the /map endpoint returns valid results with correct structure and values
    when provided a single valid dot_name, year, data column, and admin_level=2.
    Ensures fallback logic works when confidence bounds are missing.
    '''
    response = client.get("/map?dot_name=Africa:Benin&channel=unmet_need&subgroup=15-24_urban&year=2007&data=data&admin_level=2")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert results[0]["id"] == "Africa:Benin:Borgou"
    assert "value" in results[0]
    assert "data_lower_bound" in results[1]  # check fallback to value
    assert results[1]["data_lower_bound"] == results[1]["value"]


def test_map_multiple_dot_names(client):
    '''
    Tests that the /map endpoint returns an error when multiple dot_names are passed,
    which is disallowed for this endpoint.
    '''
    response = client.get("/map?dot_name=Africa:Benin,Africa:Senegal&channel=unmet_need&subgroup=15-24_urban&year=2007&data=data&admin_level=2")
    assert response.status_code == 400
    assert "one dot_name at a time" in response.text


@patch("service.controllers.map.get_dataframe", return_value=MOCK_DF)
def test_map_invalid_admin_level(mock_get_df, client):
    '''
    Tests that the endpoint rejects admin_level=1 when data is at a more granular (level 2) region.
    The system is expected to reject shallower admin levels when detailed data is requested.
    '''
    response = client.get("/map?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=15-24_urban&year=2007&data=data&admin_level=1")
    assert response.status_code == 400
    assert "shallower" in response.text


@patch("service.controllers.map.get_dataframe", side_effect=Exception("Boom"))
def test_map_internal_error(mock_df, client):
    '''
    Simulates a server-side exception during data fetching and verifies that
    the endpoint returns a 500 Internal Server Error with a helpful message.
    '''
    response = client.get("/map?dot_name=Africa:Benin&channel=unmet_need&subgroup=15-24_urban&year=2007&data=data&admin_level=2")
    assert response.status_code == 500
    assert "Internal server error" in response.text
