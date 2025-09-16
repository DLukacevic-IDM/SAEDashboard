from unittest.mock import patch
import pandas as pd
from tests.conftest import client


# Mock dataframe to simulate a successful lookup
MOCK_DF = pd.DataFrame([
    {'dot_name': 'Africa:Benin:Borgou', 'year': 1990},
    {'dot_name': 'Africa:Benin:Borgou', 'year': 1994}
])

@patch("service.controllers.years.read_shape_version", return_value=1)
@patch("service.controllers.years.read_subgroup", return_value="all")
@patch("service.controllers.years.read_channel", return_value="unmet_need")
@patch("service.controllers.years.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.years.get_dataframe", return_value=MOCK_DF)
def test_years_success(mock_get_df, mock_read_dot_names, mock_read_channel, mock_read_subgroup, mock_read_shape_version, client):
    '''
    Tests that the /years endpoint returns the correct start and end years
    for a single dot_name when matching data is found in the dataframe.
    '''
    response = client.get("/years?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=all")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "id": "Africa:Benin:Borgou",
        "start_year": 1990,
        "end_year": 1994
    }


@patch("service.controllers.years.read_shape_version", return_value=1)
@patch("service.controllers.years.read_subgroup", return_value="all")
@patch("service.controllers.years.read_channel", return_value="unmet_need")
@patch("service.controllers.years.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.years.get_dataframe", return_value=pd.DataFrame([
    {'dot_name': 'Africa:Benin:OtherProvince', 'year': 2000}
]))
def test_years_no_data_for_dotname(mock_get_df, mock_read_dot_names, mock_read_channel, mock_read_subgroup, mock_read_shape_version, client):
    '''
    Tests that the endpoint returns a 500 error when the dataset contains no records
    matching the requested dot_name, simulating a failure to resolve the range.
    '''
    response = client.get("/years?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=all")
    assert response.status_code == 500
    assert "Internal server error" in response.text


@patch("service.controllers.years.read_dot_names", return_value=["Africa:Benin", "Africa:Senegal"])
def test_years_multiple_dotnames(mock_read_dot_names, client):
    '''
    Tests that the endpoint enforces a constraint that only one dot_name
    can be requested at a time, returning a 400 error for multiple entries.
    '''
    response = client.get("/years?dot_name=Africa:Benin,Africa:Senegal&channel=unmet_need&subgroup=all")
    assert response.status_code == 400
    assert "only be requested for one dot_name" in response.text


@patch("service.controllers.years.read_shape_version", return_value=1)
@patch("service.controllers.years.read_subgroup", return_value="all")
@patch("service.controllers.years.read_channel", return_value="unmet_need")
@patch("service.controllers.years.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.years.get_dataframe", side_effect=Exception("Boom"))
def test_years_internal_error(mock_get_df, mock_read_dot_names, mock_read_channel, mock_read_subgroup, mock_read_shape_version, client):
    '''
    Simulates an unexpected internal error during data retrieval.
    Verifies that the endpoint returns a 500 Internal Server Error with the appropriate message.
    '''
    response = client.get("/years?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=all")
    assert response.status_code == 500
    assert "Internal server error" in response.text