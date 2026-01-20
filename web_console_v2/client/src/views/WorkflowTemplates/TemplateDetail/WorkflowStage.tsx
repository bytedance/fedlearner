import StateIndicator from 'components/StateIndicator';
import React, { FC } from 'react';
import { getWorkflowStage } from 'shared/workflow';
import { Workflow } from 'typings/workflow';

const WorkflowStage: FC<{ workflow: Workflow; tag?: boolean }> = ({ workflow, tag }) => {
  return <StateIndicator {...getWorkflowStage(workflow)} tag={tag} />;
};

export default WorkflowStage;
