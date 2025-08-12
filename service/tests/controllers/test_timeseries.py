import pandas as pd
from unittest.mock import patch
from tests.conftest import client


MOCK_BASIC_DF = pd.DataFrame([
    {
        'dot_name': 'Africa:Benin:Borgou',
        'year': 1990,
        'data': 0.1,
        'data_lower_bound': None,
        'data_upper_bound': None,
        'reference': None
    },
    {
        'dot_name': 'Africa:Benin:Borgou',
        'year': 1994,
        'data': 0.2,
        'data_lower_bound': 0.1,
        'data_upper_bound': 0.3,
        'reference': None
    }
])


@patch("service.controllers.timeseries.yaml.safe_load", return_value={"disaggregated_indicators": []})
@patch("service.controllers.timeseries.get_dataframe", return_value=MOCK_BASIC_DF)
@patch("service.controllers.timeseries.read_shape_version", return_value=1)
@patch("service.controllers.timeseries.read_subgroup", return_value="all")
@patch("service.controllers.timeseries.read_channel", return_value="unmet_need")
@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin:Borgou"])
def test_timeseries_basic(mock_dot_names, mock_channel, mock_subgroup, mock_version, mock_df, mock_yaml, client):
    '''
    Tests that the /timeseries endpoint returns correct yearly time series data when available.
    Validates inclusion of reference bounds when present, and omission when missing.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=all&shape_version=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["year"] == 1990
    assert "reference_lower_bound" not in data[0]
    assert data[1]["upper_bound"] == 0.3


MOCK_MONTHLY_DF = pd.DataFrame([
    {
        'dot_name': 'Africa:Benin:Borgou',
        'year': 1990,
        'month': "6",
        'data': 0.1,
        'data_lower_bound': 0.05,
        'data_upper_bound': 0.15,
        'reference': None
    }
])


@patch("service.controllers.timeseries.yaml.safe_load", return_value={"disaggregated_indicators": []})
@patch("service.controllers.timeseries.get_dataframe", return_value=MOCK_MONTHLY_DF)
@patch("service.controllers.timeseries.read_shape_version", return_value=1)
@patch("service.controllers.timeseries.read_subgroup", return_value="all")
@patch("service.controllers.timeseries.read_channel", return_value="unmet_need")
@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin:Borgou"])
def test_timeseries_monthly(mock_dot_names, mock_channel, mock_subgroup, mock_version, mock_df, mock_yaml, client):
    '''
    Tests that the endpoint correctly handles and includes monthly data in the response.
    Verifies that month and lower bound fields are populated correctly.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin:Borgou&channel=unmet_need&subgroup=all&shape_version=1")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["month"] == 6
    assert data[0]["lower_bound"] == 0.05


MOCK_DISAGG_DF = pd.DataFrame([
    {
        'dot_name': 'Africa:Benin:Borgou',
        'year': 2000,
        'data': 0.3,
        'data_lower_bound': 0.2,
        'data_upper_bound': 0.4,
        'pred_x': 0.31,
        'pred_y': 0.29,
        'reference': None
    }
])


@patch("service.controllers.timeseries.yaml.safe_load", return_value={"disaggregated_indicators": ["disagg_var"]})
@patch("service.controllers.timeseries.get_dataframe", return_value=MOCK_DISAGG_DF)
@patch("service.controllers.timeseries.read_shape_version", return_value=1)
@patch("service.controllers.timeseries.read_subgroup", return_value="all")
@patch("service.controllers.timeseries.read_channel", return_value="disagg_var")
@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin:Borgou"])
def test_timeseries_disagg(mock_dot_names, mock_channel, mock_subgroup, mock_version, mock_df, mock_yaml, client):
    '''
    Tests support for disaggregated indicators.
    Checks that predictions for multiple variables (e.g., x and y) are returned under the others field.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin:Borgou&channel=disagg_var&subgroup=all&shape_version=1")
    assert response.status_code == 200
    data = response.json()
    assert "others" in data[0]
    assert data[0]["others"]["x"] == 0.31
    assert data[0]["others"]["y"] == 0.29


@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin", "Africa:Senegal"])
def test_timeseries_multiple_dot_names(mock_dot_names, client):
    '''
    Tests that requesting multiple dot_name values returns a 400 error.
    Ensures the endpoint enforces a constraint that only one dot_name can be requested at a time.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin,Africa:Senegal&channel=x&subgroup=x&shape_version=1")
    assert response.status_code == 400
    assert "only be requested for one" in response.text


@patch("service.controllers.timeseries.get_dataframe", side_effect=Exception("Boom"))
@patch("service.controllers.timeseries.read_shape_version", return_value=1)
@patch("service.controllers.timeseries.read_subgroup", return_value="x")
@patch("service.controllers.timeseries.read_channel", return_value="x")
@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin:Borgou"])
def test_timeseries_internal_error(mock_dot_names, mock_channel, mock_subgroup, mock_version, mock_df, client):
    '''
    Simulates a server-side exception during data retrieval.
    Verifies the endpoint responds with a 500 Internal Server Error and appropriate error message.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin:Borgou&channel=x&subgroup=x&shape_version=1")
    assert response.status_code == 500
    assert "Internal server error" in response.text


@patch("service.controllers.timeseries.yaml.safe_load", return_value={})
@patch("service.controllers.timeseries.get_dataframe", return_value=pd.DataFrame([
    {'dot_name': 'Africa:Benin:OtherProvince', 'year': 2000}
]))
@patch("service.controllers.timeseries.read_shape_version", return_value=1)
@patch("service.controllers.timeseries.read_subgroup", return_value="x")
@patch("service.controllers.timeseries.read_channel", return_value="x")
@patch("service.controllers.timeseries.read_dot_names", return_value=["Africa:Benin:Borgou"])
def test_timeseries_no_data_match(mock_dot_names, mock_channel, mock_subgroup, mock_version, mock_df, mock_yaml, client):
    '''
    Tests behavior when no data matches the requested dot_name.
    Confirms the endpoint returns an empty list with a 200 status code, rather than an error.
    '''
    response = client.get("/timeseries?dot_name=Africa:Benin:Borgou&channel=x&subgroup=x&shape_version=1")
    assert response.status_code == 200
    assert response.json() == []
