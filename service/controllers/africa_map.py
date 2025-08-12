from service.helpers.controller_helpers import load_geojson_pickle
from fastapi import APIRouter

router = APIRouter()

'''
**Note: Will return 404 if Africa.shp.pickle does not exist in service/data/shapefiles
'''

@router.get("/africa_map/")
async def get_africa_map():
        """
        Retrieve pre-generated GeoJSON shape data for the African continent.

        This endpoint returns a dictionary containing a single GeoJSON FeatureCollection
        for administrative regions within Africa. The data is pre-processed and cached
        in a pickle file to improve API performance and avoid re-parsing shapefiles.

        The GeoJSON structure includes:
        - FeatureCollection wrapper
        - Multiple Feature objects, each with:
        - id: Hierarchical region identifier (e.g., "Africa:Angola:Bié")
        - properties: Region metadata (e.g., country, name, type)
        - geometry: Polygon coordinates for rendering on a map

        Returns:
        dict: A dictionary with a single key ("Africa") containing the full GeoJSON FeatureCollection.

        Example: /dot_names?dot_name=Africa
            {
                "Africa": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": "Africa:Angola:Bié",
                            "properties": {
                                "country": "angola",
                                "TYPE": 2,
                                "id": "Africa:Angola:Bié",
                                "name": "Bié"
                            },
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [
                                        [
                                            17.80353546,
                                            -13.74234009
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
        geojson = load_geojson_pickle("Africa.shp.pickle")
        return geojson
