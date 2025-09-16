from helpers.controller_helpers import get_indicator_admin_levels, read_shape_version, get_indicator_version
from service.helpers.controller_helpers import ControllerException, read_dot_names, get_channels, \
    read_admin_level, read_use_descendant_dot_names, get_indicator_time, get_indicator_subgroups
from service.helpers.dot_name import DotName
from service.schemas.IndicatorsSchema import IndicatorsListSchema
from fastapi import APIRouter, Request, HTTPException
import yaml
import os

router = APIRouter()

def generate_label(indicator):
    # if we have a specific display name known, use it
    # Load the YAML file
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../config.yaml')
    with open(full_path, "r") as file:
        config = yaml.safe_load(file)

    # Retrieve the list of indicator_labels
    indicator_labels = config.get("indicator_labels", {})

    label = indicator_labels.get(indicator, None)

    if label is None:
        # generate a display name according to a standard set of rules
        label = " ".join(p.capitalize() for p in indicator.split('_'))
    return label


@router.get("/indicators", response_model=IndicatorsListSchema)
async def get_indicators(request: Request):
    """
    Retrieves a list of indicators available for a specific region.

    This endpoint returns metadata for indicators (e.g., health metrics) available for a given
    `dot_name`, including the indicator's ID, display label, version, supported admin levels,
    available subgroups, and time coverage by year and (optionally) month.

    Query Parameters:
        - dot_name (str): A hierarchical region identifier (e.g., "Africa:Benin:Borgou").
                          Only one `dot_name` may be provided.
        - use_descendant_dot_names (bool): If True, expands search to descendant regions
                                                     of the specified dot_name (e.g., if you pass
                                                     "Africa:Senegal", the system will consider
                                                     all of Senegal's regions).
        - admin_level (int, optional): Restrict indicators to those with data available at
                                       this administrative level.

    Returns:
        dict: A dictionary with a single key `"indicators"` that maps to a list of indicator
              metadata entries, each describing one available channel (indicator) in the system.

    Example 1: /indicators?dot_name=Africa:Benin:Borgou
    return:
        {
          "indicators": [
            {
              "id": "IPTp3",
              "text": "Intermittent Preventative Treatment in Pregnancy",
              "version": 1,
              "admin_levels": [2],
              "subgroups": [
                "all"
              ],
              "time": {
                "2020": [],     # Yearly data available only (no monthly data)
                "2021": [],
                "2022": [],
                "2023": [],
                "2024": []
              }
            },
            ...
        }

    Example 2:  /indicators?dot_name=Africa:Senegal&use_descendant_dot_names=True
    return:
        {
        "indicators": [
            {
                "id": "CDM",
                "text": "CDM - Number of Nets",
                "version": 1,
                "admin_levels": [
                    1,
                    2
                ],
                "subgroups": [
                    "all"
                ],
                "time": {
                    "2019": [
                        6       # Monthly data available for each respective year
                    ],
                    "2022": [
                        6,
                        7
                    ]
                }
            },
            ...
            ]
        }
    """

    try:
        # handle get arguments
        dot_names = read_dot_names(request=request)
        if len(dot_names) > 1:
            raise HTTPException(status_code=400, detail="indicators can only be requested for one dot_name at a time.")
        dot_name = DotName(dot_name_str=dot_names[0])
        country = dot_name.country
        use_descendant_dot_names = read_use_descendant_dot_names(request=request)
        requested_admin_level = read_admin_level(request=request, required=False)
        if requested_admin_level is not None:
            if requested_admin_level < dot_name.admin_level:
                raise HTTPException(status_code=400,
                                    detail="Cannot request an admin_level shallower than the provided dot_name.")

        indicators = sorted(get_channels(dot_name=dot_name, use_descendent_dot_names=use_descendant_dot_names,
                                         admin_level=requested_admin_level))
        indicators_response = []
        for ind in indicators:
            shape_version = get_indicator_version(country, ind)
            subgroups = get_indicator_subgroups(country, ind, shape_version)
            admin_levels = get_indicator_admin_levels(country=country, channel=ind, version=shape_version)
            data_time = {}
            for subgroup in subgroups:
                subgroup_time = get_indicator_time(country=country, channel=ind, subgroup=subgroup, version=shape_version)
                for year, months in subgroup_time.items():
                    data_time.setdefault(year, []).extend(months)  # Add months to existing list
            label = generate_label(ind)
            indicators_response.append({"id": ind, "text": label, "version": shape_version, "admin_levels": list(admin_levels), "subgroups": list(subgroups), "time": data_time})

        return {"indicators": indicators_response}

    except ControllerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # re-raise deliberate FastAPI exceptions
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
