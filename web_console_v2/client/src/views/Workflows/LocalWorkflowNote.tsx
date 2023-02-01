import { IconExclamationCircle } from '@arco-design/web-react/icon';
import React, { FC, memo } from 'react';
import styled from './LocalWorkflowNode.module.less';

const LocalWorkflowNote: FC = () => {
  return (
    <div className={styled.container}>
      <IconExclamationCircle style={{ marginRight: 3 }} />
      该任务为本地任务，故无对侧配置
    </div>
  );
};

export default memo(LocalWorkflowNote);
