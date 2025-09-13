interface IndicatorConfig {
  [key: string]: {
    unitLabel: string;
    multiper: number;
    unit: string;
    mapLabel: string; // used in map popup
    decimalPt: number;
    legendLabel: string;
    useAvg?: boolean;
    mainSpeciesName?: string,
    rasterFile?: string,
    extraInfo?: boolean,
    chartType?: string,
    yAxisLabel?: string;
  };
}

export const IndicatorConfig: IndicatorConfig = {

  'modern_method': {'unitLabel': 'modern_method', 'multiper': 100, 'unit': '%',
    'mapLabel': '%', 'legendLabel': '%', 'decimalPt': 0},
  'traditional_method': {'unitLabel': 'traditional_method', 'multiper': 100, 'unit': '%',
    'mapLabel': '%', 'legendLabel': '%', 'decimalPt': 0},
  'unmet_need': {'unitLabel': 'unmet_need', 'multiper': 100, 'unit': '%',
    'mapLabel': '%', 'legendLabel': '%', 'decimalPt': 0},

};
