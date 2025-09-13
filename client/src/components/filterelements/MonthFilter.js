
/* eslint-disable object-curly-spacing */
/* eslint-disable comma-dangle */
/* eslint-disable no-unused-vars */
import React, {useState, useEffect} from 'react';
import {useDispatch, useSelector} from 'react-redux';
import {changeSelectedMonth} from '../../redux/actions/filters';
import {TimeseriesSlider} from './TimeseriesSlider';
import {injectIntl} from 'react-intl';
import PropTypes from 'prop-types';
import withStyles from '@mui/styles/withStyles';

const styles = {
  root: {
    marginTop: '5px',
    width: '100%',
  },
};

/**
 * component for month selection
 * @param {MonthFilter.propTypes} props
 * @return {React.ReactElement}
 */
const MonthFilter = (props) => {
  const {classes} = props;

  const dispatch = useDispatch();
  const currentMonth = useSelector((state) => state.filters.currentMonth);
  const indicators = useSelector((state) => state.filters.indicators);
  const primaryIndicator = useSelector((state) => state.filters.selectedIndicator);
  const currentYear = useSelector((state) => state.filters.currentYear);
  const [fromMonth, setFromMonth] = useState(0);
  const [toMonth, setToMonth] = useState(12);

  const [currentMonthLocal, changeMonthLocal] = useState(currentMonth);

  const customMarks = [
    {
      value: 0,
      label: props.intl.formatMessage({ id: 'month-All' })
    },
    {
      value: 1,
      label: props.intl.formatMessage({ id: 'month-Jan' })
    },
    {
      value: 2,
      label: props.intl.formatMessage({ id: 'month-Feb' })
    },
    {
      value: 3,
      label: props.intl.formatMessage({ id: 'month-Mar' })
    },
    {
      value: 4,
      label: props.intl.formatMessage({ id: 'month-Apr' })
    },
    {
      value: 5,
      label: props.intl.formatMessage({ id: 'month-May' })
    },
    {
      value: 6,
      label: props.intl.formatMessage({ id: 'month-Jun' })
    },
    {
      value: 7,
      label: props.intl.formatMessage({ id: 'month-Jul' })
    },
    {
      value: 8,
      label: props.intl.formatMessage({ id: 'month-Aug' })
    },
    {
      value: 9,
      label: props.intl.formatMessage({ id: 'month-Sep' })
    },
    {
      value: 10,
      label: props.intl.formatMessage({ id: 'month-Oct' })
    },
    {
      value: 11,
      label: props.intl.formatMessage({ id: 'month-Nov' })
    },
    {
      value: 12,
      label: props.intl.formatMessage({ id: 'month-Dec' })
    },
  ];
  const [localMarks, setLocalMarks] = useState(customMarks);

  useEffect(() => {
    const indicatorInfo = indicators.find((indicator) => indicator.id === primaryIndicator);

    if (indicatorInfo && currentYear) {
      const years = Object.keys(indicatorInfo.time);
      const yearInfo = indicatorInfo.time[currentYear];
      if (!yearInfo) {
        return;
      }

      console.log(customMarks);
      for (let i = 1; i <= 12; i++) {
        if (yearInfo && !yearInfo.includes(i)) {
          customMarks[i].label = '';
        }
      }
      const newMarks = customMarks.filter((mark) => {
        return mark.label !== '';
      });

      setLocalMarks(newMarks);
      setToMonth(newMarks[newMarks.length - 1].value);
    };
  }, [indicators, primaryIndicator, currentYear]);

  return (
    <div className={classes.root}>
      <TimeseriesSlider
        key="monthSlider"
        marks={localMarks}
        size='medium'
        track={false}
        min={fromMonth} max={toMonth}
        // valueLabelDisplay="auto"
        valueLabelDisplay="on"
        value={currentMonthLocal}
        step={1}
        onChange={(event, value) => {
          changeMonthLocal(value);
        }}
        onChangeCommitted={(event, value) => {
          dispatch(changeSelectedMonth(value));
        }}
      />
    </div>
  );
};

MonthFilter.propTypes = {
  intl: PropTypes.func,
  classes: PropTypes.object.isRequired,
};

export default withStyles(styles)(injectIntl(MonthFilter));
