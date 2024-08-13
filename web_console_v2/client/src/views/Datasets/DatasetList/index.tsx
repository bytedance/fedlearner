import SharedPageLayout from 'components/SharedPageLayout';
import React, { FC } from 'react';
import { Redirect, useParams } from 'react-router';
import ProcessedDatasetTodoPopover from './ProcessedDatasetTodoPopover';
import { DatasetKindLabel, DatasetTabType } from 'typings/dataset';
import { datasetKindLabelValueMap } from '../shared';
import DatasetTable from './DatasetTable';

export const DATASET_LIST_QUERY_KEY = 'fetchRawDatasetList';

const DatasetList: FC = (props) => {
  const { kind_label } = useParams<{ kind_label: DatasetKindLabel; tab?: DatasetTabType }>();

  if (!kind_label) {
    return <Redirect to={`/datasets/${DatasetKindLabel.RAW}`} />;
  }

  const kind = datasetKindLabelValueMap[kind_label];
  const isProcess = kind_label === DatasetKindLabel.PROCESSED;
  return (
    <SharedPageLayout
      title={isProcess ? '结果数据集' : '原始数据集'}
      key={kind}
      rightTitle={isProcess && <ProcessedDatasetTodoPopover />}
    >
      <DatasetTable dataset_kind={kind} />
    </SharedPageLayout>
  );
};

export default DatasetList;
