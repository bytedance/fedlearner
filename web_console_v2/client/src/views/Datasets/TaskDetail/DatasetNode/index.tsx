import React, { FC, useMemo, useState } from 'react';
import { Handle, Position, NodeComponentProps } from 'react-flow-renderer';
import WhichDataset from 'components/WhichDataset';
import { Label, LabelStrong } from 'styles/elements';
import { NodeType } from '..';
import WhichParticipantDataset from 'components/WhichParticipantDataset';
import { Dataset } from 'typings/dataset';
import styled from './index.module.less';

export type Props = NodeComponentProps<{
  title: string;
  dataset_name: string;
  dataset_uuid?: string;
  onAPISuccess?: (uuid: string, data?: any) => void;
  isActive?: boolean;
}>;

const DatasetNode: FC<Props> = ({ data, targetPosition, sourcePosition, type }) => {
  const [myDataset, setMyDataset] = useState<null | Dataset>();
  const nameJsx = useMemo(() => {
    let jsx: React.ReactNode = '';
    switch (type) {
      case NodeType.DATASET_MY:
      case NodeType.DATASET_PROCESSED:
      case NodeType.UPLOAD:
      case NodeType.DOWNLOAD:
        jsx = data?.dataset_uuid ? (
          <WhichDataset.UUID
            displayKey={type === NodeType.DOWNLOAD ? 'path' : 'name'}
            uuid={data.dataset_uuid}
            onAPISuccess={(apiData) => {
              data?.onAPISuccess?.(data.dataset_uuid!, apiData);
              setMyDataset(apiData);
            }}
          />
        ) : (
          ''
        );
        break;
      case NodeType.DATASET_PARTICIPANT:
        jsx = data?.dataset_uuid ? (
          <WhichParticipantDataset
            uuid={data.dataset_uuid}
            onAPISuccess={(apiData) => {
              data?.onAPISuccess?.(data.dataset_uuid!, apiData);
            }}
            emptyText="对方已撤销发布"
          />
        ) : (
          ''
        );
        break;
      case NodeType.LIGHT_CLIENT:
        jsx = '本地上传';
        break;
      default:
        break;
    }

    return jsx;
  }, [data, type]);

  const isCanClick =
    (type === NodeType.DATASET_MY && Boolean(myDataset)) || type === NodeType.DATASET_PROCESSED;
  return (
    <div
      className={`${styled.container} ${isCanClick && styled.can_click} ${
        data?.isActive && styled.active
      }`}
    >
      <Label isBlock>{data.title}</Label>
      <LabelStrong
        isBlock
        fontSize={14}
        className={isCanClick ? styled.can_click_label : ''}
        style={{
          wordBreak: 'break-all',
        }}
      >
        {nameJsx}
      </LabelStrong>
      {targetPosition && (
        <Handle className={styled.handle_dot} type="target" position={Position.Left} />
      )}
      {sourcePosition && (
        <Handle className={styled.handle_dot} type="source" position={Position.Right} />
      )}
    </div>
  );
};

export default DatasetNode;
