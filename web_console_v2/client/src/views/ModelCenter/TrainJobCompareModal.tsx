import React, { useMemo, useState } from 'react';
import { Modal, Table, TableColumnProps } from '@arco-design/web-react';
import { ModelJob } from 'typings/modelCenter';
import { useBatchModelJobMetricsAndConfig } from 'hooks/modelCenter';
import CONSTANTS from 'shared/constants';
import {
  LABEL_MAPPER,
  NOT_NN_ADVANCE_CONFIG_FIELD_LIST,
  NOT_TREE_ADVANCE_CONFIG_FIELD_LIST,
} from './shared';
import { isNNAlgorithm, isTreeAlgorithm } from 'views/ModelCenter/shared';
import { Variable } from 'typings/variable';
import { EnumAlgorithmProjectType } from 'typings/algorithm';

const metricRenderFunc = (val: string) => val ?? CONSTANTS.EMPTY_PLACEHOLDER;
const columns: TableColumnProps[] = [
  {
    title: '名称',
    dataIndex: 'id',
    width: 200,
  },
  {
    title: '运行参数',
    dataIndex: 'config',
    width: 300,
    render(conf) {
      return <div style={{ whiteSpace: 'pre-wrap' }}>{conf}</div>;
    },
  },
];

const treeColumns = [
  {
    title: 'ACC',
    dataIndex: 'acc',
    width: 80,
    render: metricRenderFunc,
  },
  {
    title: 'AUC',
    dataIndex: 'auc',
    width: 80,
    render: metricRenderFunc,
  },
  {
    key: 'precision',
    title: 'PRECISION',
    dataIndex: 'precision',
    width: 80,
    render: metricRenderFunc,
  },
  {
    key: 'recall',
    title: 'RECALL',
    dataIndex: 'recall',
    width: 80,
    render: metricRenderFunc,
  },
  {
    key: 'f1',
    title: 'F1',
    dataIndex: 'f1',
    width: 80,
    render: metricRenderFunc,
  },
  {
    key: 'ks',
    title: 'KS',
    dataIndex: 'ks',
    width: 80,
    render: metricRenderFunc,
  },
];

const nnColumns = [
  {
    title: 'AUC',
    dataIndex: 'auc',
    width: 80,
    render: metricRenderFunc,
  },
  {
    title: 'Log Loss',
    dataIndex: 'loss',
    watch: 80,
    render: metricRenderFunc,
  },
];

type Props = {
  visible: boolean;
  list: ModelJob[];
  algorithmType: EnumAlgorithmProjectType;
  isTraining?: boolean;
  onCancel?: () => void;
};

const TrainJobCompareModal: React.FC<Props> & { Button: React.FC<any> } = ({
  visible,
  list,
  isTraining = true,
  onCancel,
  algorithmType,
}) => {
  const { dataList, isLoading } = useBatchModelJobMetricsAndConfig(list, visible);
  const finalColumns = useMemo(() => {
    const metricColumns =
      algorithmType === EnumAlgorithmProjectType.NN_HORIZONTAL ||
      algorithmType === EnumAlgorithmProjectType.NN_VERTICAL
        ? nnColumns
        : treeColumns;
    return [...columns, ...metricColumns];
  }, [algorithmType]);
  const formattedList = useMemo(() => {
    return dataList.map((item) => {
      const metric = (isTraining ? item.metric.train : item.metric.eval) ?? {};
      const variables = item.config ?? [];
      for (const k in metric) {
        const { values = [] } = metric[k] || {};
        const numberValue = values[values.length - 1];

        if (isNaN(numberValue)) {
          metric[k] = CONSTANTS.EMPTY_PLACEHOLDER;
          continue;
        }
        metric[k] = numberValue.toFixed(3);
      }

      return {
        id: item.id,
        config: variables
          .filter((v: Variable) =>
            (isNNAlgorithm(item.job.algorithm_type)
              ? NOT_NN_ADVANCE_CONFIG_FIELD_LIST
              : isTreeAlgorithm(item.job.algorithm_type)
              ? NOT_TREE_ADVANCE_CONFIG_FIELD_LIST
              : []
            ).includes(v.name),
          )
          .map((v: Variable) => [LABEL_MAPPER[v.name] ?? v.name, v.value].join('='))
          .join('\n'),
        ...metric,
      };
    });
  }, [dataList, isTraining]);

  return (
    <Modal
      visible={visible}
      title={'训练任务对比'}
      footer={null}
      style={{ width: 1000 }}
      onCancel={onCancel}
    >
      <Table
        loading={isLoading}
        rowKey="id"
        columns={finalColumns}
        data={formattedList}
        pagination={false}
      />
    </Modal>
  );
};

const Button: React.FC<{ btnText?: string } & Omit<Props, 'visible'>> = ({
  btnText = '对比',
  ...modalProps
}) => {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <button className="custom-text-button" onClick={() => setVisible(!visible)}>
        {btnText}
      </button>
      <TrainJobCompareModal visible={visible} {...modalProps} onCancel={() => setVisible(false)} />
    </>
  );
};

TrainJobCompareModal.Button = Button;

export default TrainJobCompareModal;
