from unittest.mock import patch
import pytest
from tests.conftest import client


# Mocked dependencies
MOCK_DOT_NAME = "Africa:Senegal:Diourbel:Mbacke"
MOCK_SUBGROUPS = ["all"]
MOCK_VERSION = "1"
MOCK_DATA_TIME = "2022"
EXPECTED_INDICATOR_IDS = {
    "CDM", "CDM_Coverage", "IPTp3", "MILDA", "MILDA_Coverage", "correct_treatment",
    "incidence", "intervention_mix_pecadom",
    "malaria_death", "malaria_death_per_100000", "neg_covars", "neg_covars_category",
    "pos_covars", "pos_covars_category", "predicted_incidence", "reported_incidence",
    "testing_rates", "tpr"
}


@pytest.fixture
def mock_request_data():
    return {
        "dot_name": MOCK_DOT_NAME
    }


@patch("service.helpers.controller_helpers.read_dot_names")
@patch("service.helpers.controller_helpers.get_channels")
@patch("service.helpers.controller_helpers.get_indicator_version")
@patch("service.helpers.controller_helpers.get_indicator_subgroups")
@patch("service.helpers.controller_helpers.get_indicator_time")
def test_get_indicators_success(
    mock_get_indicator_time,
    mock_get_indicator_subgroups,
    mock_get_indicator_version,
    mock_get_channels,
    mock_read_dot_names,
    mock_request_data,
    client
):
    '''
    Test successful call to endpoint; verify attributes in returned JSON indicators
    '''
    mock_read_dot_names.return_value = [MOCK_DOT_NAME]
    mock_get_indicator_version.return_value = MOCK_VERSION
    mock_get_indicator_subgroups.return_value = MOCK_SUBGROUPS
    mock_get_indicator_time.return_value = MOCK_DATA_TIME
    mock_get_channels.return_value = list(EXPECTED_INDICATOR_IDS)

    response = client.get("/indicators", params=mock_request_data)

    assert response.status_code == 200
    data = response.json()
    assert "indicators" in data
    response_ids = {ind["id"] for ind in data["indicators"]}
    assert EXPECTED_INDICATOR_IDS.issubset(response_ids)
    for indicator in data["indicators"]:
        assert "id" in indicator
        assert "text" in indicator
        assert "time" in indicator
        assert "version" in indicator
        assert "subgroups" in indicator


@patch("service.controllers.indicators.read_dot_names", return_value=["Africa:Benin", "Africa:Mali"])
def test_get_indicators_multiple_dot_names(mock_read_dot_names, client):
    '''
    Test call to indicators endpoint only includes one dotname
    '''
    response = client.get("/indicators?dot_name=Africa:Benin,Africa:Mali")
    assert response.status_code == 400
    assert "indicators can only be requested" in response.text


@patch("service.controllers.indicators.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.indicators.read_admin_level", return_value=0)
def test_get_indicators_shallower_admin_level(mock_admin, mock_dot_names, client):
    '''
    Test that admin level provided must match level of dotname provided
    '''
    response = client.get("/indicators?dot_name=Africa:Benin:Borgou&admin_level=0")
    assert response.status_code == 400
    assert "shallower than the provided dot_name" in response.text


@patch("service.controllers.indicators.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.indicators.read_use_descendant_dot_names", return_value=False)
@patch("service.controllers.indicators.read_admin_level", return_value=None)
@patch("service.controllers.indicators.get_channels", return_value=[])
def test_get_indicators_empty(mock_channels, mock_admin, mock_descendant, mock_dot_names, client):
    '''
    Test empty json is returned when no indicators match provided dotname
    '''
    response = client.get("/indicators?dot_name=Africa:Benin:Borgou")
    assert response.status_code == 200
    assert response.json()["indicators"] == []


def test_get_indicators_missing_dot_name(client):
    '''
    Test dotname must be provided as query param
    '''
    response = client.get("/indicators")
    assert response.status_code == 400
