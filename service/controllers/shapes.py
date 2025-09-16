from collections import defaultdict

from service.helpers.dot_name import DotName
from service.helpers.controller_helpers import get_shapes, read_dot_names, read_admin_level, read_upfill, \
    ControllerException, get_all_countries_for_shapes, read_shape_version
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.get("/shapes")
async def get_features(request: Request):
    """
    Retrieves administrative boundary GeoJSON shapes for a given region and admin level.

    This endpoint returns one or more GeoJSON FeatureCollections representing the spatial
    boundaries for the requested administrative level under one or more `dot_name` inputs.
    Shapes are sourced from pre-processed shapefiles and grouped by parent `dot_name`.

    The shapes returned follow the standard GeoJSON format and include properties such as:
    - `id`: Full hierarchical dot name
    - `country`: Country name in lowercase
    - `TYPE`: Region level as an integer
    - `name`: Human-readable region name
    - `geometry`: A polygon defining the boundary

    Query Parameters:
        - dot_name (str): A region identifier (e.g., "Africa:Benin" or "Africa").
                          Multiple values allowed (comma-separated).
        - admin_level (int): The requested administrative level (e.g., 2 = province/admin1, 3 = district/admin2).
        - shape_version (int, optional): The version of the shape dataset to use.
        - upfill (bool, optional): If True, fallback to a less granular (higher) admin level
                                   if no shapes exist at the requested level.

    Returns:
        dict: A mapping of each input `dot_name` to a corresponding GeoJSON FeatureCollection.


    Example: /shapes?dot_name=Africa:Benin&admin_level=2&shape_version=1
        {
            "Africa:Benin": {
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
                            "coordinates": [
                                [
                                    [
                                        2.1917491,
                                        8.77678871
                                    ],
                                    ...
                                ]
                            ]
                        }
                    },
                    ...
                ]
            }
        }
    """
    try:
        # handle get arguments
        dot_names = read_dot_names(request=request)
        requested_admin_level = read_admin_level(request=request)
        shape_version = read_shape_version(request=request)
        upfill = read_upfill(request=request)

        shapes_by_dot_name = defaultdict(lambda: {"type": "FeatureCollection", "features": []})

        for dot_name in dot_names:
            dot_name = DotName(dot_name_str=dot_name)
            if requested_admin_level < dot_name.admin_level:
                raise ControllerException('Cannot request an admin_level shallower than the provided dot_name.')
            countries = [dot_name.country] if dot_name.country else get_all_countries_for_shapes()

            for country in countries:
                admin_level = requested_admin_level
                # TODO: shapefile version may differ from data

                dn = dot_name if dot_name.country else DotName.from_parts([dot_name.continent, country])
                shapes = get_shapes(dot_name=dn, admin_level=admin_level, version=shape_version)
                while upfill and len(shapes['features']) == 0 and admin_level > dot_name.admin_level:
                    admin_level -= 1
                    shapes = get_shapes(dot_name=dn, admin_level=admin_level, version=shape_version)

                # Extend the features with whats coming from the shapes
                shapes_by_dot_name[str(dot_name)]["features"].extend(shapes["features"])

        return shapes_by_dot_name

    except ControllerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # re-raise deliberate FastAPI exceptions
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
