import React from 'react';
import { DatasetJob, DatasetJobListItem } from 'typings/dataset';
import StateIndicator from 'components/StateIndicator';
import GridRow from 'components/_base/GridRow';
import { getDatasetJobState, getDatasetJobType } from 'shared/dataset';
import TaskActions from '../../TaskList/TaskActions';
import { Space } from '@arco-design/web-react';
import styled from './index.module.less';

type TJobTitleProp = {
  data: DatasetJob;
  onStop?: () => void;
  onDelete?: () => void;
  id: ID;
};

export default function JobTitle(prop: TJobTitleProp) {
  const { data = {} as DatasetJobListItem, onStop, onDelete, id } = prop;
  const jobData: DatasetJobListItem = {
    name: '',
    uuid: '',
    project_id: data.project_id,
    kind: data.kind,
    state: data.state,
    result_dataset_id: '',
    result_dataset_name: '',
    id,
    created_at: 0,
    coordinator_id: 0,
    has_stages: false,
  };
  return (
    <GridRow
      justify={'space-between'}
      style={{
        margin: `20px 20px 0 20px`,
      }}
    >
      <Space>
        <span className={styled.job_title_icon}>{getDatasetJobType(jobData.kind)}</span>
        <span className={styled.job_title_name}>{data.name}</span>
        <StateIndicator {...getDatasetJobState(jobData)} />
      </Space>
      <TaskActions data={jobData} onDelete={onDelete} onStop={onStop} />
    </GridRow>
  );
}
