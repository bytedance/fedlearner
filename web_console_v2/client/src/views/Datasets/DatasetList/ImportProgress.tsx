import React, { FC } from 'react';
import styled from 'styled-components';
import { BatchState, DataBatch, Dataset } from 'typings/dataset';
import StateIndicator from 'components/StateIndicator';
import { getImportedProportion, getImportStage, isImporting } from 'shared/dataset';
import { useTranslation } from 'react-i18next';

const ProgressBar = styled.div`
  position: relative;
  width: 100px;
  height: 4px;
  margin-top: 5px;
  margin-left: 15px;
  border-radius: 10px;
  background-color: var(--backgroundColorGray);
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    width: inherit;
    height: inherit;
    border-radius: inherit;
    background-color: var(--primaryColor);
    transform: translateX(var(--progress, -100%));
  }
`;

const ImportProgress: FC<{ dataset: Dataset }> = ({ dataset }) => {
  const { total, imported } = getImportedProportion(dataset);
  const proportion = Math.floor((imported / total) * 100);

  return (
    <div data-name="dataset-import-progress">
      <StateIndicator {...getImportStage(dataset)} />
      {isImporting(dataset) && (
        <ProgressBar style={{ '--progress': `${proportion - 100}%` } as any} />
      )}
    </div>
  );
};

export const DataBatchImportProgress: FC<{ batch: DataBatch }> = ({ batch }) => {
  const { t } = useTranslation();
  const { state, num_file, imported_file_num } = batch;
  const proportion = Math.floor((imported_file_num / num_file) * 100);

  const isImporting = state === BatchState.IMPORTING;

  const indicatorPorps: React.ComponentProps<typeof StateIndicator> = {
    [BatchState.IMPORTING]: {
      type: 'processing',
      text: t('dataset.state_importing', { total: num_file, imported: imported_file_num }),
    },
    [BatchState.FAILED]: { type: 'error', text: t('dataset.state_error') },
    [BatchState.SUCCESS]: { type: 'success', text: t('dataset.state_available') },
    [BatchState.NEW]: { type: 'success', text: t('dataset.state_available') },
  }[state];

  return (
    <div data-name="data-batch-import-progress">
      <StateIndicator {...indicatorPorps} />

      {isImporting && <ProgressBar style={{ '--progress': `${proportion - 100}%` } as any} />}
    </div>
  );
};

export default ImportProgress;
