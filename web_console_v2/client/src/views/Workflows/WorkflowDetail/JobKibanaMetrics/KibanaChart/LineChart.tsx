import React, { FC, memo, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import { KiabanaMetrics } from 'typings/kibana';
import { formatTimestamp } from 'shared/date';
import { IconPen } from '@arco-design/web-react/icon';
import { ControlButton } from 'styles/elements';
import defaultTheme from 'styles/theme';
import styled from './LineChart.module.less';

type Props = {
  metrics: KiabanaMetrics;
  label: string;
  isFill: boolean;
  onEditParams: () => void;
};

const OPTIONS = {
  scales: {
    yAxes: [
      {
        ticks: {
          beginAtZero: false,
        },
      },
    ],
    x: {
      grid: {
        display: false,
      },
    },
  },
};

const KibanaLineChart: FC<Props> = memo(({ metrics, label, isFill, onEditParams }) => {
  const data = useMemo(() => {
    return _processData(metrics, { label });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label, metrics.length]);

  return (
    <div style={{ width: '100%' }}>
      {/*
       * @NOTE: Since react-chartjs-2 will always keep initial ratio after first render
       * we give two size of chart on purpose for different size of container
       */}
      {isFill ? (
        <Line key="fullscreen" data={data} options={OPTIONS} width={900} height={300} />
      ) : (
        <Line key="non-fullscreen" data={data} options={OPTIONS} width={435} height={300} />
      )}

      {isFill && (
        <div className={styled.controls_container}>
          <ControlButton onClick={() => onEditParams()}>
            <IconPen />
          </ControlButton>
        </div>
      )}
    </div>
  );
});

function _processData(metrics: KiabanaMetrics, { label }: { label: string }) {
  return {
    labels: metrics.map(([time]) => formatTimestamp(time, 'M-DD HH:mm')),
    datasets: [
      {
        label,
        data: metrics.map(([, value]) => value),
        fill: false,
        backgroundColor: defaultTheme.primaryColor,
        borderColor: defaultTheme.blue4,
        borderWidth: 1,
      },
    ],
  };
}

export default KibanaLineChart;
