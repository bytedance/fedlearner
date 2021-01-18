import StateIndicator from 'components/StateIndicator';
import React, { FC } from 'react';
import { getWorkflowStage } from 'shared/workflow';
import { Workflow } from 'typings/workflow';

const WorkflowStage: FC<{ data: Workflow; tag?: boolean }> = ({ data, tag }) => {
  return <StateIndicator {...getWorkflowStage(data)} tag={tag} />;
};

export default WorkflowStage;
