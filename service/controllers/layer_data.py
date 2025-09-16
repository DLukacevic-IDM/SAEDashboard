import json
import os
from service.helpers.controller_helpers import ControllerException
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/layer_data/")
async def get_layer_data():
    """
    Retrieves pre-processed geospatial layer data.

    This endpoint returns a nested JSON object containing region-specific data layers
    for use in map visualizations. It is preloaded from a cached JSON file (`layer_data.json`)
    and includes spatial and analytical metadata for specific sites.

    The data is typically used to enrich geospatial dashboards with values such as:
    - site coordinates
    - genetic or molecular marker frequencies
    - sample counts
    - health facility attributes

    Returns:
        dict: A nested dictionary containing geospatial and contextual metadata per country and site.

     Example: /layer_data
     return:
        {
            "Senegal": {
                "BarcodeData": {
                    "2019": {
                        "site_data": {
                            "SUGAR COMPANY CLINIC": {
                                "CODE": "CSS",
                                "ALT": "RT_CS",
                                "TYPE": "NS_HP",
                                "GPS_2_Source": "Original",
                                "Lat_2": 16.47,
                                "Long_2": -15.71,
                                "Fraction_unique": 1,
                                "Fraction_polygenomic": 0.667,
                                "repeated_twice": 0,
                                "repeated_multiple": 0,
                                "heterozygosity": 0.0284,
                                "n": 26
                            },
                            "DIAWAR": {
                                "CODE": "DWR",
                                "ALT": "RT_DW",
                                "TYPE": "NS_HP",
                                "GPS_2_Source": "Original",
                                "Lat_2": 16.4614,
                                "Long_2": -16.0516,
                                "Fraction_unique": null,
                                "Fraction_polygenomic": null,
                                "repeated_twice": null,
                                "repeated_multiple": null,
                                "heterozygosity": null,
                                "n": 1
                            },
                            ...
                    }
                }
            }
        }

     """

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.join(current_dir, '..', 'data', 'layer_data.json')
        with open(file, 'r') as f:
            data = json.load(f)
        return data
    except ControllerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # re-raise deliberate FastAPI exceptions
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
