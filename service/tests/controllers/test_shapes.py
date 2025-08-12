from unittest.mock import patch
from tests.conftest import client


# Sample feature stub
MOCK_FEATURES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "Africa:Benin:Borgou",
            "properties": {
                "country": "benin",
                "TYPE": 2,
                "id": "Africa:Benin:Borgou",
                "name": "Borgou"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[2.1917, 8.7767], [2.192, 8.777], [2.193, 8.778]]]
            }
        }
    ]
}

@patch("service.controllers.shapes.read_dot_names", return_value=["Africa:Benin"])
@patch("service.controllers.shapes.read_admin_level", return_value=2)
@patch("service.controllers.shapes.read_shape_version", return_value=1)
@patch("service.controllers.shapes.read_upfill", return_value=False)
@patch("service.controllers.shapes.get_shapes", return_value=MOCK_FEATURES)
@patch("service.controllers.shapes.get_all_countries_for_shapes", return_value=["Benin"])
def test_shapes_success(
    mock_get_countries,
    mock_get_shapes,
    mock_read_upfill,
    mock_read_version,
    mock_read_admin,
    mock_read_dot_names,
        client
):
    '''
    Test that the /shapes endpoint returns valid GeoJSON features when provided
    a valid dot_name, admin_level, and shape_version, and upfill is not requested.
    '''
    response = client.get("/shapes?dot_name=Africa:Benin&admin_level=2&shape_version=1")
    assert response.status_code == 200
    result = response.json()
    assert "Africa:Benin" in result
    assert result["Africa:Benin"]["type"] == "FeatureCollection"
    assert isinstance(result["Africa:Benin"]["features"], list)


@patch("service.controllers.shapes.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.shapes.read_admin_level", return_value=1)
@patch("service.controllers.shapes.read_shape_version", return_value=1)
@patch("service.controllers.shapes.read_upfill", return_value=False)
def test_shapes_admin_level_too_shallow(
    mock_upfill, mock_version, mock_admin, mock_dots, client
):
    '''
    Test that the /shapes endpoint returns a 400 error when the requested
    admin_level is shallower than the granularity of the provided dot_name.
    '''
    response = client.get("/shapes?dot_name=Africa:Benin:Borgou&admin_level=1")
    assert response.status_code == 400
    assert "shallower than the provided dot_name" in response.text


@patch("service.controllers.shapes.read_dot_names", return_value=["Africa:Benin"])
@patch("service.controllers.shapes.read_admin_level", return_value=2)
@patch("service.controllers.shapes.read_shape_version", return_value=1)
@patch("service.controllers.shapes.read_upfill", return_value=True)
@patch("service.controllers.shapes.get_shapes")
@patch("service.controllers.shapes.get_all_countries_for_shapes", return_value=["Benin"])
def test_shapes_with_upfill(
    mock_get_countries,
    mock_get_shapes,
    mock_read_upfill,
    mock_read_version,
    mock_read_admin,
    mock_read_dot_names,
        client
):
    '''
    Test that the /shapes endpoint uses upfill logic when no shapes are found
    at the requested level and returns fallback shapes from a higher level.
    '''
    # Simulate first call with no features, then fallback returns valid features
    mock_get_shapes.side_effect = [
        {"type": "FeatureCollection", "features": []},  # first (empty)
        MOCK_FEATURES  # upfill fallback
    ]

    response = client.get("/shapes?dot_name=Africa:Benin&admin_level=2&shape_version=1")
    assert response.status_code == 200
    assert response.json()["Africa:Benin"]["features"][0]["id"] == "Africa:Benin:Borgou"


@patch("service.controllers.shapes.read_upfill", return_value=False)
@patch("service.controllers.shapes.read_shape_version", return_value=1)
@patch("service.controllers.shapes.read_admin_level", return_value=2)
@patch("service.controllers.shapes.read_dot_names", return_value=["Africa:Benin"])
@patch("service.controllers.shapes.get_shapes", side_effect=Exception("Unexpected"))
def test_shapes_internal_error(mock_get_shapes, mock_read_dot_names, mock_read_admin_level, mock_read_version, mock_read_upfill, client):
    '''
    Test that the /shapes endpoint handles unexpected server errors
    during shape retrieval and returns a 500 Internal Server Error.
    '''
    response = client.get("/shapes?dot_name=Africa:Benin&admin_level=2&shape_version=1")
    assert response.status_code == 500
    assert "Internal server error" in response.text
