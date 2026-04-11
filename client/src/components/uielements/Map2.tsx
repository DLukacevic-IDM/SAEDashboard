/* eslint-disable camelcase */
/* eslint-disable max-len */
/* eslint-disable no-unused-vars */
import React, {useRef, useEffect, useLayoutEffect, useState, useContext} from 'react';
import {useSelector, useDispatch} from 'react-redux';
import {GeoJSON, LayerGroup, LeafletMouseEvent, FeatureGroup, GeoJSONOptions, Map} from 'leaflet';
import MapLegend from './Legends/MapLegend.js';
import {Feature, GeometryObject} from 'geojson';
import chroma, {Color} from 'chroma-js';
import customTheme from '../../customTheme.json';
import {extraInfo} from './MapUtil';
import {makeStyles} from '@mui/styles';
import 'leaflet/dist/leaflet.css';
import * as _ from 'lodash';
import {injectIntl} from 'react-intl';
import {IndicatorConfig} from '../constTs.tsx';
import {ComparisonMapContext} from '../provider/comparisonMapProvider';
import {Typography, Tooltip} from '@mui/material';
import {FormattedMessage} from 'react-intl';
// Export Image Component
import ExportImageComponent from '../uielements/ExportImage.js';

const styles = makeStyles({
  MapContainer: {
    backgroundColor: 'white',
    height: '100%',
  },
  mapTitle: {
    position: 'absolute',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center', // vertical centering
    top: 13,
    left: 0,
    right: 0,
    width: '100%', // ensure it fills the parent
    height: 30,
    zIndex: 100,
    pointerEvents: 'none', // allows clicks to pass through
  },
  note_diff: {
    position: 'absolute',
    fontSize: '0.8rem',
    // backgroundColor: 'yellow',
    padding: '0 5px',
    left: 13,
    whiteSpace: 'pre-wrap',
    display: 'flex',
    width: 'fit-content',
    marginRight: 70,
    bottom: 0,
    alignItems: 'center',
  },
  extraInfo: {
    marginLeft: 5,
    color: 'white',
    backgroundColor: '#256baf',
    cursor: 'pointer',
    padding: '0 5px',
  },
  flex: {
    display: 'flex',
    width: 'fit-content',
  },
});

/**
 * Interfaces
 */
interface MapExtension extends Map {
  _layers: FeatureGroup[]
}

interface CustomTheme {
  color: string,
  values: string[]
}

// interface StateFilter

const extenededlegendTheme: CustomTheme[] = customTheme;

const IncidenceMap = ['reported_incidence',
  'predicted_incidence',
  'model_predictions',
  'low_model_predictions',
  'incidence',
];

export const isIncidenceMap = (indicator:string) => {
  return IncidenceMap.includes(indicator);
};

const MapComponent = (props: any) => {
  const {mapData, geoJson, height, selectPlace, selectedMapTheme, primary, indicator, intl} = props;
  const selectedLegend = useSelector((state:any) => state.filters.selectedLegend);
  const selectedDiffMap = useSelector((state:any) => state.filters.selectedDiffMap);
  const selectedLegendSync = useSelector((state:any) => state.filters.selectedLegendSync);
  const layerData = useSelector((state:any) => state.dashboard.layerData);
  const currentYear = useSelector((state:any) => state.filters.currentYear);
  const currentMonth = useSelector((state:any) => state.filters.currentMonth);
  const selectedYear = useSelector((state:any) => state.filters.selectedYear);
  const primaryIndicator = useSelector((state:any) => state.filters.selectedIndicator);
  const mapLegendMax = useSelector((state:any) => state.filters.mapLegendMax);
  const mapLegendMin = useSelector((state:any) => state.filters.mapLegendMin);
  const [selectedLayer, setSelectedLayer] = useState('');
  const [unselectedLayer, setUnselectedLayer] = useState('');
  const mapLabel = IndicatorConfig[indicator] ?
    intl.formatMessage({id: IndicatorConfig[indicator].mapLabel}) : '';
  const rasterFile = IndicatorConfig[indicator] ? IndicatorConfig[indicator].rasterFile : '';

  const indicatorConfig = IndicatorConfig[indicator] || {
    unitLabel: indicator, multiper: 1, unit: '', mapLabel: '%',
    decimalPt: 2, legendLabel: '%',
  };
  const mainSpeciesName = indicatorConfig.mainSpeciesName;
  const hasExtraInfo = indicatorConfig.extraInfo;
  const {latLngClicked, setLatLngClicked, zoom, setZoom, center, setCenter, closePopup, setClosePopup} = useContext(ComparisonMapContext);
  const dispatch = useDispatch();

  // Data-related variables

  const minValueFromData = _.get(_.minBy(mapData, 'value'), 'value');
  const maxValueFromData = _.get(_.maxBy(mapData, 'value'), 'value');
  let maxValue = (selectedDiffMap || !selectedLegendSync) ? maxValueFromData : mapLegendMax;
  let minValue = (selectedDiffMap || !selectedLegendSync) ? minValueFromData : mapLegendMin;

  if (selectedDiffMap && !primary) {
    if (maxValue > minValue * -1) {
      minValue = maxValue * -1;
    } else {
      maxValue = minValue * -1;
    }
  }

  const numberOfSteps: number = 10;
  const isCovariateMap = () => {
    if (primary) {
      return primaryIndicator == 'neg_covars' || primaryIndicator == 'pos_covars';
    } else {
      return indicator == 'neg_covars' || indicator == 'pos_covars';
    }
  };

  const isCovariateCategoryMap = () => {
    if (primary) {
      return primaryIndicator == 'neg_covars_category' || primaryIndicator == 'pos_covars_category';
    } else {
      return indicator == 'neg_covars_category' || indicator == 'pos_covars_category';
    }
  };
  const legend = useRef(null);

  interface FeatureAddOn extends GeoJSONOptions {
    name: string,
    NAME: string,
    clicked: boolean,
    iso_a3: string,
  };

  const classes = styles();
  const chart = useRef() as React.MutableRefObject<HTMLDivElement>;
  let [mapObj, setMapObj] = useState<MapExtension>();
  let geojson: GeoJSON;

  /**
   * for setting up a feature (place ) on the map
   * @param {*} feature
   * @param {*} layer
   */
  const onEachFeature = function(feature: Feature<GeometryObject, FeatureAddOn>, layer: LayerGroup) {
    const layerFeature = layer.feature as Feature<GeometryObject, FeatureAddOn>;

    const placeName = feature.properties.name || feature.properties.NAME;

    layerFeature.properties['name'] = placeName;

    layer.on({
      mouseover: (e) => highlightFeature(e, null, false),
      mouseout: resetHighlight,
      click: ((e: LeafletMouseEvent) => {
        if (feature && feature.id) {
          selectPlace(feature.id);
        }
      }),
    });
  };

  const highlightFeature = (e: any, color: string = null, fromEffect: boolean) => {
    const feature = e.target;
    feature.setStyle({
      weight: 3,
      color: color ? color : '#FFCE74',
      dashArray: '',
      fillOpacity: 0.9,
    });

    if (e.latlng && !fromEffect) {
      setLatLngClicked({...e.latlng, LGA: feature.feature.properties.name});
    };

    showPopup(e, false);
  };

  const showPopup = (e: any, fromEffect: boolean) => {
    const feature = e.target;
    if (feature && feature.feature) {
      const region = _.find(mapData, {id: feature.feature.id});

      if (region) {
        const regionName = region.id.split(':').splice(2).join(':');
        let entireMsg = regionName;
        if (region.others) {
          // for indicators with additional data
          const rowHTML = (val1: string, val2: string, val3: string) => (
            '<div class="row"><div class="col">' + val1 + '</div><div>' + val2 + val3 + '</div></div>'
          );
          entireMsg = '<div class="popupCustom">';
          entireMsg += '<div class="row border"><div class="col">'+ regionName +'</div></div>';
          entireMsg += rowHTML(mainSpeciesName, Number((region.value * indicatorConfig.multiper).toFixed(indicatorConfig.decimalPt)).toLocaleString(), mapLabel);

          for (const key in region.others) {
            if (key) {
              if (isNaN(region.others[key])) {
                entireMsg += rowHTML(intl.formatMessage({id: key}), region.others[key], '');
              } else {
                entireMsg += rowHTML(key, Number((region.others[key] * indicatorConfig.multiper).toFixed(indicatorConfig.decimalPt)).toLocaleString(), mapLabel);
              }
            }
          }
          entireMsg += '</div>';
        } else {
          entireMsg += ' : <b>' + Number((region.value * indicatorConfig.multiper).toFixed(indicatorConfig.decimalPt)).toLocaleString() +
          '</b> ' + mapLabel + '<br/>';
        };

        window.L.popup()
            .setLatLng(e.latlng)
            .setContent(entireMsg)
            .openOn(mapObj);
      } else {
      // todo: commented out as it is causing issue in
      // no data popup
      // const region = feature.feature.id.split(':').splice(2).join(':');
      // window.L.popup()
      //     .setLatLng(e.latlng)
      //     .setContent(region + ': <b>' + intl.formatMessage({id: 'NoData_short'}) +'</b>')
      //     .openOn(mapObj);
      }
    }
  };

  const resetHighlight = (e: LeafletMouseEvent) => {
    geojson.resetStyle(e.target);
  };

  const themeStr = _.find(extenededlegendTheme, {color: selectedMapTheme as any});

  const scale = chroma.scale(themeStr ? themeStr.values : selectedMapTheme).domain([minValue, maxValue]).classes(numberOfSteps);

  /**
   * Map setup
   */
  const mapSetup = function() {
    const L = require('leaflet');
    const initialView = [14.4, -15];

    if (mapObj) {
      return;
    }

    mapObj = L.map(chart.current, {
      zoomSnap: 0.25,
      zoomDelta: 0.25,
      scrollWheelZoom: false}).setView(initialView, 6.8) as MapExtension;


    const standardFeatureHandler = (feature:Feature) => {
      const region = _.find(mapData, {id: feature.id as any});
      if (region && region.value != null) {
        const colors = _.get(_.find(customTheme, {color: selectedMapTheme as any}), 'values');

        let color2 = 'grey';
        try {
          color2 = !isCovariateMap() ? scale(region.value) :
            colors[region.value-1];
        } catch (e) {
          // todo: log error
          console.log('Error in color setting');
        }
        return {fillColor: isCovariateMap() ? '' : color2, fillOpacity: isCovariateMap() ? 0.02 : 0.7, fill: true, color: 'grey', weight: 1};
      } else {
        return {color: 'grey', weight: 1, fillColor: ''};
      }
    };

    // create map layer
    geojson = L.geoJSON(geoJson, {
      style: (feature: Feature) => {
        return standardFeatureHandler(feature);
      },
      onEachFeature: onEachFeature,
    });

    geojson.addTo(mapObj);

    const layerControl = L.control.layers().addTo(mapObj);

    const stationClicked = (station: RainfallStation) => {
      dispatch(changeSelectedRainfallStation(station.Station));
    };

    mapObj.on('overlayadd', (data)=>{
      if (_.get(data, 'layer.options._zIndex')) { // mostly for district names
        data.layer.setZIndex(data.layer.options._zIndex);
      }
      setSelectedLayer(data.name);
      setUnselectedLayer(null);
    });
    mapObj.on('overlayremove', (data)=>{
      setUnselectedLayer(data.name);
      setSelectedLayer(null);
    });
    comparisonEventSetup(mapObj);
    setMapObj(mapObj);
  };

  const comparisonEventSetup = (mapObj: MapExtension) => {
    // setup events
    mapObj.on('zoomend', () => {
      setZoom(mapObj.getZoom());
    });
    mapObj.on('dragend', () => {
      setCenter(mapObj.getCenter());
    });
  };

  /**
   * to find a map feature when a LGA is given
   * @param {*} mapObj
   * @param {*} latLng
   * @return {*} a leaflet feature
   */
  const findFeatureByLGA = (mapObj: any, latLng:any) => {
    if (!mapObj) return;
    const feature = _.find(mapObj._layers, (layer) => {
      if (layer.feature) {
        const f: any = layer.feature;
        return f.properties['name'] === latLng.LGA;
      } else {
        return false;
      }
    });
    return feature;
  };

  // update zoom for comparisom map
  useEffect(() => {
    if (mapObj && zoom > 0) {
      mapObj.setZoom(zoom);
    }
  }, [zoom]);
  // update pan for comparisom map
  useEffect(() => {
    if (mapObj && center) {
      mapObj.panTo([center.lat, center.lng]);
    }
  }, [center]);

  /**
  * for opening popup for the 2nd map on the comparison maps
  */
  useEffect(() => {
    // if (forCompare) {
    const feature = findFeatureByLGA(mapObj, latLngClicked);

    if (feature) {
      const mouseEvent : any = {
        target: feature,
        latlng: latLngClicked,
      };
      showPopup(mouseEvent, true);
    }
  }, [latLngClicked]);

  /**
   * Component Initialization
   */
  useLayoutEffect(() => {
    mapSetup();
    return (() => {
      if (mapObj) {
        mapObj.remove();
        mapObj = null;
      }
    });
  }, []);

  const dataSourceMsg = intl.formatMessage({id: 'data_source_'+indicator});

  return (
    <div style={{position: 'relative', width: '100%', height: '100%', minHeight: height, overflow: 'hidden'}}>
      <div
        ref={chart}
        style={{position: 'relative', width: '100%', height: '100%'}}
      >
        <div className={classes.mapTitle}>
          {/* Map Title */}
          <Typography variant="h5">{intl.formatMessage({id: indicator})}</Typography>
        </div>
        <div ref={chart} className={classes.MapContainer} id="chartContainer">
          <ExportImageComponent
            targetNode={chart.current}
            fileName="map.png"
          />
        </div>
        {/* Map Legend */}
        <MapLegend minValue={minValue} numberOfSteps={numberOfSteps} mapLegendMax={maxValue}
          selectedMapTheme={selectedMapTheme} legend={legend} primary={primary} selectedLayer={selectedLayer}
          unselectedLayer={unselectedLayer}
          selectedIndicator={indicator}
          key={minValue + maxValue + selectedLayer + indicator} />

        {/* Difference note */}
        {!primary && selectedDiffMap &&
          <div className={classes.note_diff}>
            {intl.formatMessage({id: 'difference_calculate_by'}) + ' : ' +
              indicator + ' ' +
            intl.formatMessage({id: 'in'}) + ' ' +
            selectedYear + ' - ' + primaryIndicator + ' ' +
            intl.formatMessage({id: 'in'}) + ' ' +
            currentYear}
          </div>
        }
        {/* Caveat note */}
        {
          <div className={classes.note_diff}>
            {/* <div className={classes.flex} title={dataSourceMsg}>
              {dataSourceMsg}
            </div> */}
            {hasExtraInfo &&
              <div>
                <Tooltip title={extraInfo(indicator)}
                  componentsProps={{
                    tooltip: {
                      sx: {
                        minWidth: 500,
                      },
                    },
                  }}
                >
                  <div className={classes.extraInfo}>
                    <FormattedMessage id="extra_info" />
                  </div>
                </Tooltip>
              </div>
            }
          </div>
        }
      </div>
    </div>
  );
};

export default injectIntl(MapComponent);
