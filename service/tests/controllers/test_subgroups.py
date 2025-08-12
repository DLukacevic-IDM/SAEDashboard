from unittest.mock import patch
from tests.conftest import client


def test_subgroups_nodata(client):
    """
    Checks that an incorrect country name will not yield subgroups
    """
    res = client.get("/subgroups?dot_name=Africa:Fake")
    assert res.json()['subgroups'] == []

@patch("service.controllers.subgroups.get_subgroups", return_value=["15-24_urban", "25plus_urban"])
@patch("service.controllers.subgroups.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.subgroups.read_use_descendant_dot_names", return_value=False)
@patch("service.controllers.subgroups.read_admin_level", return_value=None)
def test_subgroups_success(mock_level, mock_descendant, mock_dot_names, mock_get_subgroups, client):
    """
    Checks that a call to /subgroups yields correct subgroups
    """
    response = client.get("/subgroups?dot_name=Africa:Benin:Borgou")
    assert response.status_code == 200
    data = response.json()
    assert "subgroups" in data
    assert data["subgroups"][0]["id"] == "15-24_urban"
    assert data["subgroups"][0]["text"] == "15-24 Urban"


@patch("service.controllers.subgroups.read_dot_names", return_value=["Africa:Benin", "Africa:Senegal"])
def test_subgroups_multiple_dot_names(mock_read, client):
    """
    Checks that a call to /subgroups can only have one dot_name
    """
    response = client.get("/subgroups?dot_name=Africa:Benin,Africa:Senegal")
    assert response.status_code == 400
    assert "only be requested for one" in response.text


@patch("service.controllers.subgroups.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.subgroups.read_admin_level", return_value=1)
@patch("service.controllers.subgroups.read_use_descendant_dot_names", return_value=False)
def test_subgroups_invalid_admin_level(mock_desc, mock_level, mock_dot_names, client):
    """
    Checks that admin_level provided must match level of dot_name
    """
    response = client.get("/subgroups?dot_name=Africa:Benin:Borgou&admin_level=1")
    assert response.status_code == 400
    assert "shallower" in response.text


@patch("service.controllers.subgroups.read_admin_level", return_value=None)
@patch("service.controllers.subgroups.read_use_descendant_dot_names", return_value=False)
@patch("service.controllers.subgroups.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.subgroups.get_subgroups", side_effect=Exception("Unexpected"))
def test_subgroups_internal_error(mock_get_subgroups, mock_read_dot_names, mock_read_use_desc, mock_read_admin_level, client):
    '''
    Test that the /subgroups endpoint returns a 500 error with an appropriate message
    when an unexpected exception occurs during subgroup retrieval.
    '''
    response = client.get("/subgroups?dot_name=Africa:Benin:Borgou")
    assert response.status_code == 500
    assert "Internal server error" in response.text
