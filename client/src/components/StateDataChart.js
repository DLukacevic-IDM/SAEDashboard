/* eslint-disable no-unused-vars */
/* eslint-disable guard-for-in */
import React, {useEffect, useState} from 'react';
import {Typography} from '@mui/material';
import EventLineChart from './uielements/EventLineChart';
import axios from 'axios';
import withStyles from '@mui/styles/withStyles';
import loader from '../image/loader.gif';
import {showError} from '../redux/actions/messaging';
import {useDispatch, useSelector} from 'react-redux';
import PropTypes from 'prop-types';
import {FormattedMessage} from 'react-intl';
import config from '../app_config.json';
import {IndicatorConfig} from './constTs.tsx';
import StackedBarChart from './uielements/StackedBarChart';

const styles = {
  title: {
    textAlign: 'center',
    width: '100%',
    marginTop: 20,
  },
  noDataOrLoading: {
    minHeight: 350,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  root: {
    border: 'solid 1px lightgrey',
  },
};

const StateDataChart = (props) => {
  const {classes, group, groupName, selectedState, channel} = props;
  const [data, setData] = useState(null);
  const [isError, setIsError] = useState(false);
  const selectedLocale = useSelector((state) => state.filters.selectedLanguage);

  const shapeFileVersion = config.shapefileVersion[channel] ?
    config.shapefileVersion[channel] : 1;

  const dispatch = useDispatch();
  useEffect(() => {
    const fetchData = async () => {
      setIsError(false);
      axios.defaults.baseURL = process.env.API_BASE_URL || '/api';
      try {
        const result = await axios(
            '/timeseries?dot_name=' + selectedState + '&channel=' + channel + '&subgroup=' +
            group + '&shape_version=' + shapeFileVersion,
        );
        for (const item of result.data) {
          item.month = parseInt(item.month);
        }
        if (channel == 'intervention_mix_pecadom') {
          // filter out interventions with 0's
          // this is a workaround to avoid showing interventions with 0's
          // in the chart, as they are not useful
          result.data = result.data.map((annualData) => {
            const filteredData = {};
            for (const key in annualData.others) {
              if (Object.hasOwn(annualData.others, key)) {
                if (annualData.others[key] == 1) {
                  filteredData[key] = 1; // only keep interventions with 1's
                };
              };
            };
            annualData.others = filteredData;
            return annualData;
          });
        }

        setData(result.data);
      } catch (error) {
        let errMsg = 'Error occurred.';
        if (data && data.response && data.response.data) {
          errMsg = data.response.data;
        }
        // dispatch(showError(errMsg));
        setIsError(true);
      }
    };

    // Only fetch if a state and group are selected!
    if (selectedState && group && channel) {
      fetchData();
    }
  }, [selectedState, channel, group, selectedLocale]);

  if (!data && !isError && selectedState) {
    return (
      <div className={classes.noDataOrLoading}>
        <img src={loader} alt={'Loading...'}/>
      </div>);
  };

  if (!selectedState && !isError) {
    return (
      <div className={classes.noDataOrLoading}>
        <FormattedMessage id='SelectStateOrDistrict'/>
      </div>);
  };

  return (
    <div className={classes.root}>
      <Typography variant="subtitle2" className={classes.title}>
        <FormattedMessage id={groupName}/>
      </Typography>

      {
        isError ?
          <div className={classes.noDataOrLoading}>
            Error loading chart data...</div> :
          (
            (IndicatorConfig[channel].chartType == 'stackBar' ||
              IndicatorConfig[channel].chartType == 'bar') ?
            <StackedBarChart chartData={data} title={group}
              channel={IndicatorConfig[channel].mainSpeciesName}
              indicator={channel}
              barType={IndicatorConfig[channel].chartType}
              selectedState={selectedState} /> :
            <EventLineChart chartData={data} title={group} channel={channel}
              selectedState={selectedState} />
          )
      }
    </div>
  );
};

StateDataChart.propTypes = {
  classes: PropTypes.object,
  group: PropTypes.string,
  groupName: PropTypes.string,
  selectedState: PropTypes.string,
  channel: PropTypes.string,
};

export default withStyles(styles)(StateDataChart);

