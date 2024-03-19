/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import { Line } from 'react-chartjs-2';

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
        borderColor: 'rgb(53, 162, 235)',
      },
    ],
  };

  return finalData;
};

const defaultMaxValue = 1;

const getDefaultOptions = (maxValue = 1) => ({
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      display: false,
      position: 'top',
    },
    title: {
      display: false,
    },
  },
  scales: {
    x: {
      offset: true,
      grid: {
        color: 'transparent',
        tickColor: '#cecece',
      },
    },
    y: {
      grid: {
        borderColor: 'transparent',
      },
    },
  },
});

const LineChart: FC<Props> = ({
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

  return <Line data={data} options={options || defaultOptions} width={width} height={height} />;
};

export default LineChart;
