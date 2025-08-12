from unittest.mock import patch, mock_open
import json
from tests.conftest import client

# Sample valid data to mock
mock_layer_data = {
    "Senegal": {
        "Health Center A": {
            "lat": 14.716677,
            "long": -17.467686
        },
        "Health Center B": {
            "lat": 15.6142,
            "long": -16.2287
        }
    }
}

@patch("service.controllers.layer_data.open", new_callable=mock_open, read_data=json.dumps(mock_layer_data))
def test_get_layer_data_success(mock_file, client):
    '''
    Test successful endpoint call
    '''
    response = client.get("/layer_data/")
    assert response.status_code == 200
    assert response.json() == mock_layer_data


@patch("service.controllers.layer_data.open", new_callable=mock_open, read_data="{invalid_json:")
def test_get_layer_data_invalid_json(mock_file, client):
    '''
    Test json must be valid
    '''
    response = client.get("/layer_data/")
    assert response.status_code == 500  # Raised as an unhandled exception


@patch("service.controllers.layer_data.open", side_effect=FileNotFoundError("File missing"))
def test_get_layer_data_file_not_found(mock_file, client):
    '''
    Test health clinics file must exist
    '''
    response = client.get("/layer_data/")
    assert response.status_code == 500