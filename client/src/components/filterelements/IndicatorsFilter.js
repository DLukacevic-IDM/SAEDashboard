/* eslint-disable no-unused-vars */
import React from 'react';
import {useSelector} from 'react-redux';
import {ListSubheader, MenuItem, Select} from '@mui/material';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import PropTypes from 'prop-types';
import {FormattedMessage} from 'react-intl';
import {makeStyles} from '@mui/styles';

// import * as _ from 'lodash';
const styles = makeStyles({
  menuItem: {
    paddingLeft: '30px',
    lineHeight: '15px',
  },
  subHeader: {
    textTransform: 'uppercase',
    // textDecoration: 'underline',
    fontWeight: 'bold',
    color: 'white',
    backgroundColor: 'grey',
    lineHeight: '30px',
  },
});
/**
 * component for indicator selection
 * @param {IndicatorFilter.propTypes} props
 * @return {React.ReactElement}
 */
const IndicatorFilter = (props) => {
  const {selectedIndicator, changeIndicator, changeIsAdm3, primary} = props;
  const indicators = useSelector((state) => state.filters.indicators);
  const selectedIsAdm3 = useSelector((state) => state.filters.isAdm3);
  const classes = styles();

  return (
    <FormControl variant="standard">
      <InputLabel htmlFor="indicator-select">
        <FormattedMessage id='indicators'/>
      </InputLabel>
      <Select id="indicator-select" value={selectedIndicator || ''}
        onChange={(e) => {
          const _indicator = e.target.value;
          const indicatorInfo = indicators.find((indicator) => indicator.id === _indicator);
          if (indicatorInfo) {
            const adminLevel = selectedIsAdm3 ? 2 : 1;
            if (!indicatorInfo.admin_levels.includes(adminLevel) && primary) {
              changeIsAdm3(!selectedIsAdm3);
            }
          }
          changeIndicator(_indicator);
        }}
      >
        {indicators.map((field, i) => {
          return (<MenuItem value={field.id} key={i}>{field.text}</MenuItem>);
        })}
      </Select>
    </FormControl>);
};

IndicatorFilter.propTypes = {
  selectedIndicator: PropTypes.string,
  changeIndicator: PropTypes.func,
  changeIsAdm3: PropTypes.func,
  primary: PropTypes.bool,
};

export default IndicatorFilter;
