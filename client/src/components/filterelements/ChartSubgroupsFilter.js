import React from 'react';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormGroup from '@mui/material/FormGroup';
import Switch from '@mui/material/Switch';
import * as _ from 'lodash';
import PropTypes from 'prop-types';
import {injectIntl} from 'react-intl';

/**
 * component for a list of switches for toggling the display of charts
 * @param {ChartSubgroupsFilter.propTypes} props
 * @return {React.ReactElement}
 */
const ChartSubgroupsFilter = (props) => {
  const {groups, selectedGroups, toggleGroup} = props;

  // Handel toggle switch
  const handleCheck = (e) => {
    toggleGroup(e.target.value);
  };

  // Create switches group
  const switches = groups.map((option) => {
    return (
      <FormControlLabel key={option} label={props.intl.formatMessage({id: option})}
        control={
          <Switch key={option} color="primary"
            checked={_.includes(selectedGroups, option)}
            onChange={handleCheck} value={option}
          />}
      />
    );
  });

  return (
    <FormGroup row>
      {switches}
    </FormGroup>
  );
};

ChartSubgroupsFilter.propTypes = {
  groups: PropTypes.array,
  selectedGroups: PropTypes.array,
  toggleGroup: PropTypes.func,
  intl: PropTypes.func,
};


export default injectIntl(ChartSubgroupsFilter);
