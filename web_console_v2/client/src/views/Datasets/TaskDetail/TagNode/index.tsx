import React, { FC } from 'react';
import { Handle, Position, NodeComponentProps } from 'react-flow-renderer';
import { DataJobBackEndType } from 'typings/dataset';
import styled from './index.module.less';

export type Props = NodeComponentProps<{
  title: string;
  dataset_job_uuid: string;
  workflow_uuid: string;
  kind: DataJobBackEndType;
  job_id: ID;
}>;

const TagNode: FC<Props> = ({ data, targetPosition, sourcePosition }) => {
  return (
    <div className={styled.container}>
      <span
        className={styled.label}
        style={{ color: Boolean(data.job_id) ? 'var(--primaryColor)' : 'var(--textColor)' }}
        title={data.title}
      >
        {data.title}
      </span>
      {targetPosition && (
        <Handle className={styled.handle_dot} type="target" position={Position.Left} />
      )}
      {sourcePosition && (
        <Handle className={styled.handle_dot} type="source" position={Position.Right} />
      )}
    </div>
  );
};

export default TagNode;
