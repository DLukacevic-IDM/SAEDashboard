/* eslint-disable object-curly-spacing */
/* eslint-disable no-unused-vars */
import React from 'react';
import {VictoryChart, VictoryBar, VictoryGroup, VictoryTheme, VictoryLegend,
  VictoryTooltip, VictoryLabel,
  VictoryStack,
} from 'victory';
import withStyles from '@mui/styles/withStyles';
import PropTypes from 'prop-types';
import {injectIntl} from 'react-intl';
import {IndicatorConfig} from '../constTs.tsx';

const styles = ({
  title: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: '1.25rem',
  },
  root: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',

  },
  chartContainer: {
    maxWidth: 1000,
    height: '100%',
  },
});

const StackedBarChart = (props) => {
  const {chartData, classes, channel, barType, intl, indicator} = props;
  const transformedData = [];
  const channelConfig = IndicatorConfig[indicator];

  console.log(barType);

  // first pass to get 'Gambia' data
  const mainData = [];
  chartData.forEach((data) => {
    const year = data.year;
    const transformedItem = {
      x: year.toString(),
      y: data.middle,
      label: `${channel}: ${Math.round(data.middle)}%`,
      labelOnly: channel,
    };
    mainData.push(transformedItem);
  });
  transformedData.push(mainData);

  // second pass to get 'others' data
  if (chartData.length > 0) {
    Object.keys(chartData[0].others).forEach((item) => {
      const othersData = [];
      chartData.forEach((data) => {
        const year = data.year;
        const others = data.others;
        if (others) {
          const transformedItem = {
            x: year.toString(),
            y: data.others[item],
            label: `${item}: ${Math.round(data.others[item])}${channelConfig.unit}`,
            labelOnly: item,
          };
          othersData.push(transformedItem);
        }
      });
      transformedData.push(othersData);
    });
  };

  const bars = (barWidth) => {
    return (
      transformedData.map((data, index) => {
        return (
          <VictoryBar
            barWidth={barWidth}
            labelComponent={<VictoryTooltip />}
            key={index}
            data={data}
          />
        );
      })
    );
  };

  return (
    <div className={classes.root}>
      <div className={classes.chartContainer}>
        { transformedData[0].length > 0 &&
          <VictoryChart
            domainPadding={{x: 20}}
            theme={VictoryTheme.clean}
            width={600}
            padding={{'top': 20, 'right': 20, 'bottom': 120, 'left': 50}}
          >
            <VictoryLabel x={6} y={130}
              text={`${channelConfig['yAxisLabel']}`}
              angle={-90}
            />
            {
              barType === 'bar' ?
                <VictoryGroup
                  domainPadding={{x: 20}}
                  offset={10}
                  colorScale={'qualitative'}
                >
                  { bars(9)}
                </VictoryGroup> :
                <VictoryStack>
                  { bars(20)}
                </VictoryStack>
            }
            <VictoryLegend
              itemsPerRow={3}
              x={20}
              y={220}
              borderPadding={{'top': 0, 'right': 0, 'bottom': 0, 'left': 10}}
              data={transformedData.map((s) => {
                return ({
                  name: s && s.length > 0 ? s[0].labelOnly : '',
                });
              })}
            />
          </VictoryChart>
        }
      </div>
    </div>
  );
};

StackedBarChart.propTypes = {
  classes: PropTypes.object,
  chartData: PropTypes.array.isRequired,
  channel: PropTypes.string,
  barType: PropTypes.string,
  intl: PropTypes.object,
  indicator: PropTypes.string,
};

export default withStyles(styles)(injectIntl(StackedBarChart));
