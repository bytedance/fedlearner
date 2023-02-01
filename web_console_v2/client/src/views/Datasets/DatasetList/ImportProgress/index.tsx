import React, { FC, useContext } from 'react';
import { BatchState, DataBatch, Dataset, DatasetKindBackEndType } from 'typings/dataset';
import StateIndicator from 'components/StateIndicator';
import { getImportStage, isFrontendSucceeded } from 'shared/dataset';
import { GlobalDatasetIdToErrorMessageMapContext } from '../DatasetTable';
import { Tag } from '@arco-design/web-react';
import './index.less';

const ImportProgress: FC<{ dataset: Dataset; tag?: boolean }> = ({ dataset, tag = false }) => {
  const { type, text, tip } = getImportStage(dataset);
  const isEmptyDataset = (dataset?.file_size || 0) <= 0 && isFrontendSucceeded(dataset);
  const isInternalProcessed = dataset.dataset_kind === DatasetKindBackEndType.INTERNAL_PROCESSED;
  const globalDatasetIdToErrorMessageMap = useContext(GlobalDatasetIdToErrorMessageMapContext);
  const errorMessage = globalDatasetIdToErrorMessageMap[dataset.id as number] ?? '';

  return (
    <div data-name="dataset-import-progress" className={'import-progress-wrapper'}>
      <StateIndicator type={type} text={text} tip={errorMessage || tip} tag={tag} />
      {isEmptyDataset && !isInternalProcessed && (
        <Tag className={'dataset-empty-tag'} color="purple" size="small">
          空集
        </Tag>
      )}
    </div>
  );
};

export const DataBatchImportProgress: FC<{ batch: DataBatch }> = ({ batch }) => {
  const { state } = batch;

  const indicatorPorps: React.ComponentProps<typeof StateIndicator> = ({
    [BatchState.IMPORTING]: {
      type: 'processing',
      text: '导入中',
    },
    [BatchState.FAILED]: { type: 'error', text: '导入失败' },
    [BatchState.SUCCESS]: { type: 'success', text: '可用' },
    [BatchState.NEW]: { type: 'success', text: '可用' },
  } as const)[state];

  return (
    <div data-name="data-batch-import-progress">
      <StateIndicator {...indicatorPorps} />
    </div>
  );
};

export default ImportProgress;
