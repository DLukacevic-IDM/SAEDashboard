/* eslint-disable max-len */
import React, {useEffect} from 'react';
import Paper from '@mui/material/Paper';
import withStyles from '@mui/styles/withStyles';
import {useDispatch, useSelector} from 'react-redux';
import {
  changeSelectedIndicator, changeSelectedComparisonIndicator,
  changeSelectedMapTheme, changeSelectedComparisonMapTheme,
  changeSelectedState, changeSelectedComparisonState,
  changeIsAdm3,
  changeSelectedSubgroup,
  changeSelectedComparisonSubgroup,
} from '../redux/actions/filters';
import Filters from './MapPanelFilter';
import MapPanelMap from './MapPanelMap';
import * as _ from 'lodash';
import PropTypes from 'prop-types';
import {FormattedMessage} from 'react-intl';


const styles = {
  root: {
    marginBottom: '1em',
    padding: 5,
    margin: 5,
  },
  comparisonMapBar: {
    background: '#2196f3',
  },
};

const MapPanel = (props) => {
  const {classes, primary} = props;
  const dispatch = useDispatch();
  const indicators = useSelector((state) => state.filters.indicators);
  const selectedIndicator = useSelector((state) => state.filters.selectedIndicator);
  const selectedSubgroup = useSelector((state) => state.filters.selectedSubgroup);
  const selectedComparisonIndicator = useSelector(
      (state) => state.filters.selectedComparisonIndicator);
  const selectedSubgroupComparison = useSelector((state) => state.filters.selectedComparisonSubgroup);
  const subgroups = _.find(indicators, {id: selectedIndicator})?.subgroups || [];
  const subgroupsComparison = _.find(indicators, {id: selectedComparisonIndicator})?.subgroups || [];
  const selectedMapThemeRedux = useSelector((state) => state.filters.selectedMapTheme);
  const selectedComparisonMapThemeRedux = useSelector((state) =>
    state.filters.selectedComparisonMapTheme);

  const selectedYear = useSelector((state) => state.filters.selectedYear);
  const currentYear = useSelector((state) => state.filters.currentYear);
  const isAdm3 = useSelector((state) => state.filters.isAdm3);

  // Handle changing indicator for main map.
  const changeSelectedIndicatorHandler = (indicator) => {
    dispatch(changeSelectedIndicator(indicator));
  };

  const changeIsAdm3Handler = (isAdm3) => {
    dispatch(changeIsAdm3(isAdm3));
  };

  // Handle changing indicator for main map.
  const changeSelectedComparisonIndicatorHandler = (indicator) => {
    dispatch(changeSelectedComparisonIndicator(indicator));
  };

  // Handle changing the map theme color for primary map.
  const changeSelectedMapThemeRedux = (mapTheme) => {
    dispatch(changeSelectedMapTheme(mapTheme));
  };

  // Handle changing the map theme color for comparison map.
  const changeSelectedComparisonMapThemeRedux = (mapTheme) => {
    dispatch(changeSelectedComparisonMapTheme(mapTheme));
  };

  // Handle changing the selected state.
  const setSelectedState = (state) => {
    // if (selectedIndicator == selectedComparisonIndicator) {
    // if same indicator is selected on both map, user is allowed
    // see different time series plot on 2 different locations
    if (primary) {
      dispatch(changeSelectedState(state));
    } else {
      dispatch(changeSelectedComparisonState(state));
    }
    // } else {
    //   dispatch(changeSelectedState(state));
    //   dispatch(changeSelectedComparisonState(state));
    // }
  };

  // By default assign the first element
  if (subgroups.length !== 0 && !subgroups.includes(selectedSubgroup)) {
    dispatch(changeSelectedSubgroup(primary && subgroups.includes('all') ? 'all' : subgroups[0]));
  }
  if (subgroupsComparison.length !== 0 && !subgroupsComparison.includes(selectedSubgroupComparison)) {
    dispatch(changeSelectedComparisonSubgroup(!primary && subgroupsComparison.includes('all') ? 'all' : subgroupsComparison[0]));
  }

  useEffect(()=>{
    dispatch(changeSelectedSubgroup(null));
    dispatch(changeSelectedComparisonSubgroup(null));
  }, [indicators.length, selectedIndicator, isAdm3]);

  const changeSubgroup = (primary, subgroup) => {
    if (primary) {
      dispatch(changeSelectedSubgroup(subgroup));
    } else {
      dispatch(changeSelectedComparisonSubgroup(subgroup));
    }
  };


  return (
    <Paper className={classes.root}>
      <Filters
        title={primary ?
          <FormattedMessage id='main_map' /> : <FormattedMessage id='comparison_map' />}
        changeSubgroup={changeSubgroup}
        changeIndicator={primary ? changeSelectedIndicatorHandler :
          changeSelectedComparisonIndicatorHandler}
        changeIsAdm3={changeIsAdm3Handler}
        changeMapTheme={changeSelectedMapThemeRedux}
        changeComparisonMapTheme={changeSelectedComparisonMapThemeRedux}
        selectedSubgroup={primary ? selectedSubgroup : selectedSubgroupComparison}
        selectedIndicator={primary ? selectedIndicator : selectedComparisonIndicator}
        selectedMapTheme={selectedMapThemeRedux}
        selectedComparisonMapTheme={selectedComparisonMapThemeRedux}
        parentClasses={primary ? {} : classes}
        primary={primary} />
      <MapPanelMap changeSelectedState={setSelectedState}
        subgroup={primary ? selectedSubgroup: selectedSubgroupComparison}
        indicator={primary ? selectedIndicator: selectedComparisonIndicator}
        key={selectedIndicator+selectedComparisonIndicator+selectedSubgroup+
          + selectedSubgroupComparison+
          primary ? currentYear : selectedYear}
        primary={primary}/>
    </Paper>
  );
};

MapPanel.propTypes = {
  classes: PropTypes.any,
  primary: PropTypes.bool,
};

export default withStyles(styles)(MapPanel);

