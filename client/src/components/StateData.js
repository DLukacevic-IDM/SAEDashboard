/* eslint-disable no-unused-vars */
import React, {useEffect, useState} from 'react';
import {Grid, Typography} from '@mui/material';
import withStyles from '@mui/styles/withStyles';
import StateDataChart from './StateDataChart';
import ChartSubgroupsFilter from './filterelements/ChartSubgroupsFilter';
import * as _ from 'lodash';
import Paper from '@mui/material/Paper';
import {Toolbar, AppBar, Link} from '@mui/material';
import {ChartContext} from '../components/context/chartContext';
import PropTypes from 'prop-types';
import {FormattedMessage} from 'react-intl';

const styles = {
  title: {
    textAlign: 'center',
    width: '100%',
    marginTop: 5,
    marginLeft: 25,
    fontSize: 15,
  },
  chartArea: {
    padding: 5,
    margin: '-10px 5px 0px 5px',
    minHeight: 478,
  },
  toggles: {
    textAlign: 'center',
    width: '1000px',
    margin: '0 auto',
    marginBottom: 10,
  },
  grow: {
    flexGrow: 1,
  },
  chartBar: {
    marginBottom: 5,
  },
  linkContainer: {
    display: 'flex',
    flexDirection: 'column',
    marginTop: 5,
    marginRight: -15,
    width: 80,
  },
  link: {
    color: 'white',
    textAlign: 'right',
    cursor: 'pointer',
  },
};

const StateData = (props) => {
  const {classes, selectedState, indicators, channel} = props;

  const [subgroups, setSubgroups] = useState([]);
  const [selectedGroups, setSelectedGroups] = useState([]);

  const [maxYAxisVal, setMaxYAxisVal] = useState(0);
  const [minYAxisVal, setMinYAxisVal] = useState(1000);

  const contextValue = {maxYAxisVal, setMaxYAxisVal, minYAxisVal, setMinYAxisVal};
  const indObj = _.find(indicators, {'id': channel});

  /** show all groups */
  const showAll = () => {
    setSelectedGroups(indObj.subgroups);
  };

  /** hide all groups */
  const hideAll = () => {
    setSelectedGroups([]);
  };

  useEffect(() => {
    const indObj = _.find(indicators, {'id': channel});

    if (indObj) {
      setSubgroups(indObj.subgroups);
      setSelectedGroups(indObj.subgroups);
    }

    // Only fetch if a state is selected!
    if (selectedState) {
      setMaxYAxisVal(0);
      setMinYAxisVal(1000);
    }
  }, [selectedState, indicators.length, channel]);

  useEffect(()=> {
    setMaxYAxisVal(0);
    setMinYAxisVal(1000);
  }, [selectedGroups.length, channel]);

  const toggleGroup = (toggleGroup) => {
    const index = _.indexOf(selectedGroups, toggleGroup);

    // If we have the index present -> remove it
    if (index !== -1) {
      setSelectedGroups([...selectedGroups.filter((group) => group !== toggleGroup)]);
    } else {
      // Was not present -> add it back using order from subgroups
      const newGroups = [...selectedGroups, toggleGroup];
      const newSelectedGroups = subgroups.filter((group) => {
        if (newGroups.indexOf(group) > -1) {
          return group;
        }
      });
      setSelectedGroups(newSelectedGroups.map( (group)=>group));
    }
  };

  // Dont display anything if we do not have the subgroups yet
  if (subgroups.length === 0) {
    return null;
  }


  return (
    <Paper className={classes.chartArea}>
      {/* app bar charts */}
      <AppBar position="static" >
        <Toolbar variant="dense" className={classes.chartBar}>
          <Typography variant="h6" className={classes.title}>
            {selectedState} ({indObj ? indObj['text'] : '' })
          </Typography>
          <div className={classes.grow} key={1}/>
          <div className={classes.linkContainer} key={2}>
            <Link className={classes.link} onClick={showAll}>
              <Typography variant="subtitle2">
                <FormattedMessage id="show_all"/>
              </Typography>
            </Link>
            <Link className={classes.link} onClick={hideAll}>
              <Typography variant="subtitle2">
                <FormattedMessage id="hide_all"/>
              </Typography>
            </Link>
          </div>
        </Toolbar>
      </AppBar>

      <ChartContext.Provider value={contextValue}>
        <div className={classes.toggles}>
          <ChartSubgroupsFilter groups={subgroups}
            selectedGroups={selectedGroups}
            toggleGroup={toggleGroup}/>
        </div>
        <Grid container spacing={1} >
          {selectedGroups.map((group) => {
            return (
              <Grid item xs={12} md={12} key={group} >
                <StateDataChart
                  group={group}
                  groupName={group}
                  selectedState={selectedState}
                  channel={channel}
                  key={channel+selectedState}
                />
              </Grid>
            );
          })}
        </Grid>
      </ChartContext.Provider>
    </Paper>
  );
};

StateData.propTypes = {
  classes: PropTypes.object,
  selectedState: PropTypes.string,
  indicators: PropTypes.array,
  channel: PropTypes.string,
};

export default withStyles(styles)(StateData);

