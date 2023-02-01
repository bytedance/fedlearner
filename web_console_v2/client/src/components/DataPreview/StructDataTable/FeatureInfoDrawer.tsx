/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import { Drawer, DrawerProps, Grid, Button, Table } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import { CaretDown, CaretUp, Close } from 'components/IconPark';
import { Bar } from 'react-chartjs-2';
import { floor } from 'lodash-es';
import { CONSTANTS } from 'shared/constants';

import styles from './FeatureInfoDrawer.module.less';

const { Row } = Grid;

type HistDataset = {
  data: number[];
  label?: string;
  backgroundColor?: string;
};

export const formatChartData = (labels: number[], datasets: HistDataset[]) => ({
  labels: labels
    .map((v) => floor(v, 1))
    .reduce((acc, curr, index, arr) => {
      if (arr[index + 1]) {
        acc.push(`[${curr}, ${arr[index + 1]}]`);
      }
      return acc;
    }, [] as string[]),

  datasets: datasets.map((data) => {
    return Object.assign({ label: '数据集', backgroundColor: '#468DFF' }, data);
  }),
});

interface Props extends DrawerProps {
  data?: any[];
  histData?: ReturnType<typeof formatChartData>;
  compareWithBase?: boolean;
  loading?: boolean;
  featureKey?: string;
  toggleVisible: (val: boolean) => void;
  onClose?: () => void;
}

const barChartOptions: Chart.ChartOptions = {
  scales: {
    xAxes: [
      {
        ticks: {
          beginAtZero: false,
          fontSize: 8,
        },
      },
    ],
  },
};

export const METRIC_KEY_TRANSLATE_MAP: { [key: string]: string } = {
  count: '样本数',
  mean: '平均值',
  stddev: '标准差',
  min: '最小值',
  max: '最大值',
  missing_count: '缺失数',
  missing_rate: '缺失率',
};

export const FEATURE_DRAWER_ID = 'feature_drawer';

const FeatureInfoDrawer: FC<Props> = ({
  featureKey,
  data,
  histData,
  loading,
  onClose,
  toggleVisible,
  compareWithBase,
  ...props
}) => {
  const columns = useMemo(() => {
    return !compareWithBase
      ? [
          {
            title: '参数',
            dataIndex: 'key',
            width: '100px',
          },
          {
            title: '求交数据集',
            dataIndex: 'value',
          },
        ]
      : [
          {
            title: '参数',
            dataIndex: 'key',
            width: '100px',
          },
          {
            title: '原始数据集',
            dataIndex: 'baseValue',
          },

          {
            title: '求交数据集',
            dataIndex: 'value',
          },
          {
            title: '对比',
            dataIndex: 'diff',
            render: (val: any, record: { baseValue: number; diff: number; isPercent: boolean }) => {
              let isShowUpIcon = false;

              // If isPercent = true, diff is string, like '99%','-88%'
              if (record.isPercent) {
                const strDiff = String(record.diff);
                isShowUpIcon =
                  strDiff.length > 0 ? strDiff[0] !== CONSTANTS.EMPTY_PLACEHOLDER : false;
              } else {
                isShowUpIcon = val >= 0;
              }

              return (
                <GridRow gap={5}>
                  {isShowUpIcon ? (
                    <CaretUp style={{ color: 'var(--successColor)' }} />
                  ) : (
                    <CaretDown style={{ color: 'var(--errorColor)' }} />
                  )}
                  {record.isPercent
                    ? record.diff
                    : floor((record.diff / (record.baseValue || 1)) * 100, 2) + '%'}
                </GridRow>
              );
            },
          },
        ];
  }, [compareWithBase]);
  return (
    <Drawer
      maskStyle={{ backdropFilter: 'blur(3px)' }}
      width="520px"
      onCancel={closeDrawer}
      headerStyle={{ display: 'none' }}
      footer={null}
      focusLock={true}
      maskClosable={true}
      {...props}
    >
      <div id={FEATURE_DRAWER_ID} style={{ height: '100%' }}>
        <Row
          id={FEATURE_DRAWER_ID}
          className={styles.drawer_header}
          align="center"
          justify="space-between"
        >
          <Row align="center">
            <h3 className={styles.feature_key}>{featureKey}</h3>
          </Row>
          <GridRow gap="10">
            <Button size="small" icon={<Close />} onClick={closeDrawer} />
          </GridRow>
        </Row>

        <Table
          className={`${styles.info_table} custom-table`}
          rowKey={'key'}
          size="small"
          columns={columns}
          pagination={false}
          data={data ?? []}
          loading={loading}
        />
        {histData && (
          <div className={styles.chart_container}>
            <Bar data={histData} options={barChartOptions} />
          </div>
        )}
      </div>
    </Drawer>
  );

  function closeDrawer() {
    toggleVisible && toggleVisible(false);
    onClose && onClose();
  }
};

export default FeatureInfoDrawer;
