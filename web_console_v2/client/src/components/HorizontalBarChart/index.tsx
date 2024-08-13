/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import { Bar } from 'react-chartjs-2';

type Item = {
  label: string;
  value: any;
};

type Props = {
  valueList: Item[];
  formatData?: (valueList: Item[]) => any;
  options?: any;
  width?: number;
  height?: number;
  maxValue?: number;
};

const defaultFormatData = (valueList: Item[]) => {
  const labels: any[] = [];
  const data: any[] = [];

  valueList.forEach((item) => {
    labels.push(item.label);
    data.push(item.value);
  });

  const finalData = {
    labels,
    datasets: [
      {
        data,
        backgroundColor: '#468DFF',
        borderWidth: 0,
        barPercentage: 0.6,
      },
    ],
  };

  return finalData;
};

const defaultMaxValue = 1;

const getDefaultOptions = (maxValue = 1) => ({
  maintainAspectRatio: false,
  indexAxis: 'y',
  // Elements options apply to all of the options unless overridden in a dataset
  // In this case, we are setting the border of each horizontal bar to be 2px wide
  elements: {
    bar: {
      borderWidth: 0,
    },
  },
  responsive: true,
  plugins: {
    legend: {
      display: false,
    },
    title: {
      display: false,
    },
  },
  scales: {
    y: {
      grid: {
        color: 'transparent',
        tickColor: '#cecece',
      },
    },
    x: {
      grid: {
        drawBorder: false,
      },
      min: 0,
      // max: maxValue * 1.2,
      // ticks: {
      //   min: 0,
      //   max: maxValue * 1.2,
      //   suggestedMin: 0,
      //   suggestedMax: maxValue * 1.2,
      //   stepSize: 0.2,
      // },
    },
  },
});

const HorizontalBarChart: FC<Props> = ({
  valueList,
  formatData = defaultFormatData,
  options,
  width,
  height,
  maxValue = defaultMaxValue,
}) => {
  const data = useMemo(() => {
    return formatData(valueList);
  }, [valueList, formatData]);

  const defaultOptions = useMemo(() => {
    return getDefaultOptions(maxValue);
  }, [maxValue]);

  return <Bar data={data} options={options || defaultOptions} width={width} height={height} />;
};

export default HorizontalBarChart;
