/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';

import { CONSTANTS } from 'shared/constants';

import { Table, Collapse } from '@arco-design/web-react';
import CodeEditor from 'components/CodePreview';
import { IconCaretRight } from '@arco-design/web-react/icon';

import { ColumnProps } from '@arco-design/web-react/es/Table';
import { AlgorithmProject, Algorithm } from 'typings/algorithm';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantId } from 'hooks';

const SectionTitle = styled.p<{ hasMargin?: boolean }>`
  margin-top: ${(props) => (props.hasMargin ? '20px' : '0')};
  font-size: 12px;
  font-weight: bold;
  color: var(--color-text-1);
`;
const RequiredAsterisk = styled.span`
  display: inline-block;
  margin-left: 0.2em;
  font-size: 1.8em;
  color: rgb(var(--red-6));
  line-height: 0.5em;
  vertical-align: bottom;
`;
const StyledCollapse = styled(Collapse)`
  .arco-collapse-item-header {
    position: relative;
    border-bottom: none;
    padding-left: 0;
    padding-bottom: 0;
  }

  .arco-collapse-item .arco-collapse-item-icon-hover {
    left: 3em;
    right: unset;
    // note: 和下面的自定义 expandIcon 相对应
    transform: translateY(-65%);
  }

  .arco-collapse-item-content-box {
    padding: 0;
    background: transparent;
  }

  .arco-collapse-item .arco-collapse-item-icon-hover-right > .arco-collapse-item-header-icon-down {
    transform: rotate(90deg);
  }
`;

const CollapseItem = Collapse.Item;
const tables: ColumnProps[] = [
  {
    dataIndex: 'name',
    title: '名称',
    render(val: string) {
      return val || CONSTANTS.EMPTY_PLACEHOLDER;
    },
  },
  {
    dataIndex: 'value',
    title: '默认值',
    render(val: string) {
      return val || CONSTANTS.EMPTY_PLACEHOLDER;
    },
  },
  {
    dataIndex: 'required',
    title: '是否必填',
    render(required: boolean) {
      return (
        <span>
          {required ? '是' : '否'}
          {required ? <RequiredAsterisk /> : null}
        </span>
      );
    },
  },
  {
    dataIndex: 'comment',
    title: '提示语',
    render(val: string) {
      return val || CONSTANTS.EMPTY_PLACEHOLDER;
    },
  },
];

type Props = {
  type: 'algorithm_project' | 'algorithm' | 'pending_algorithm';
  detail?: AlgorithmProject | Algorithm;
  isParticipant?: boolean;
};

const AlgorithmInfo: FC<Props> = ({ isParticipant, type, detail }) => {
  const participantId = useGetCurrentProjectParticipantId();
  const projectId = useGetCurrentProjectId();
  let Editor: React.FC<any>;

  switch (type) {
    case 'algorithm':
      Editor = isParticipant ? CodeEditor.PeerAlgorithm : CodeEditor.Algorithm;
      break;
    case 'pending_algorithm':
      Editor = CodeEditor.PendingAlgorithm;
      break;
    case 'algorithm_project':
    default:
      Editor = CodeEditor.AlgorithmProject;
      break;
  }

  if (!detail) {
    return null;
  }

  return (
    <>
      <StyledCollapse bordered={false} defaultActiveKey={['table']} expandIconPosition="right">
        <CollapseItem
          header={<SectionTitle>超参数</SectionTitle>}
          expandIcon={<IconCaretRight />}
          name="table"
        >
          <Table
            columns={tables}
            data={detail?.parameter?.variables}
            pagination={false}
            rowKey={(record) => record.name}
          />
        </CollapseItem>
      </StyledCollapse>
      <SectionTitle hasMargin={true}>算法代码</SectionTitle>
      <Editor
        id={detail.id}
        isAsyncMode={true}
        projId={projectId}
        participantId={participantId}
        uuid={detail.uuid}
        height={type === 'algorithm' ? '100%' : '480px'}
      />
    </>
  );
};

export default AlgorithmInfo;
