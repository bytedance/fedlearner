/* istanbul ignore file */

import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Collapse } from '@arco-design/web-react';

import { formatLanguage } from 'shared/helpers';

import { Resizable } from 're-resizable';
import CodeEditor from 'components/CodeEditor';
import FileExplorer, { FileDataNode } from 'components/FileExplorer';

const Content = styled.div`
  display: flex;
  flex: 1;
  height: 443px;
`;

const StyledCollapse = styled(Collapse)`
  // when <FileExplorer/> resizing, max-width + overflow will trigger <CodeEditor/> automaticLayout
  // I dont know why calc(100%) or calc(100% - 0px) not work,so I set calc(100% - 1px)
  max-width: calc(100% - 1px);

  .ant-collapse-content > .ant-collapse-content-box {
    padding: 0;
  }
  .ant-collapse-header {
    background-color: #fff;
  }
`;

const StyledResizable = styled(Resizable)`
  position: relative;
  padding: 12px 0;
  border-right: 1px solid var(--lineColor);
  &::after {
    position: absolute;
    right: 0px;
    content: '';
    width: 1px;
    background-color: var(--lineColor);
  }
`;

const Right = styled.div`
  flex: 1;
  // when <FileExplorer/> resizing, max-width + overflow will trigger <CodeEditor/> automaticLayout
  overflow: hidden;
`;

const Title = styled.span`
  display: inline-block;
  margin-right: 12px;
  color: #1d252f;
  font-size: 13px;
  font-weight: 500;
`;
const Label = styled.span`
  display: inline-block;
  padding: 0 6px;
  border-radius: 2px;
  background: #e8f4ff;
  font-size: 12px;
  color: var(--primaryColor);
`;

type Props = {
  title?: string;
  label?: string;
  style?: React.CSSProperties;
  fileData: { [filePath: string]: string };
  isLoading?: boolean;
};

type Key = string | number;

export const MIN_FILE_TREE_WIDTH = 270;
export const MAX_FILE_TREE_WIDTH = 600;

const resizeableDefaultSize = {
  width: MIN_FILE_TREE_WIDTH,
  height: 'auto',
};
const resizeableEnable = {
  right: true,
};

const CodePreviewCollapse: FC<Props> = ({ title, label, fileData, style, isLoading }) => {
  const [currentCode, setCurrentCode] = useState('');
  const [currentLanguage, setCurrentLanguage] = useState<
    'json' | 'python' | 'javascript' | 'java' | 'go'
  >('python');

  return (
    <StyledCollapse expandIconPosition="right" defaultActiveKey="1" style={style}>
      <Collapse.Item
        header={
          <>
            <Title>{title}</Title>
            {label && <Label>{label}</Label>}
          </>
        }
        name="1"
      >
        <Content>
          <StyledResizable
            defaultSize={resizeableDefaultSize}
            maxWidth={MAX_FILE_TREE_WIDTH}
            enable={resizeableEnable}
          >
            <FileExplorer
              isReadOnly={true}
              isLoading={isLoading}
              fileData={fileData}
              onSelect={onSelect as any}
            />
          </StyledResizable>
          <Right>
            <CodeEditor
              isReadOnly={true}
              language={currentLanguage}
              value={currentCode}
              theme="grey"
            />
          </Right>
        </Content>
      </Collapse.Item>
    </StyledCollapse>
  );

  function onSelect(
    selectedKeys: Key[],
    info: {
      selected: boolean;
      node: FileDataNode;
      selectedNodes: FileDataNode[];
      e: Event;
    },
  ) {
    // folder or file
    if (
      info.selected &&
      info.selectedNodes &&
      info.selectedNodes[0] &&
      !info.selectedNodes[0].isFolder
    ) {
      setCurrentCode(info.selectedNodes[0]?.code ?? '');
      setCurrentLanguage(formatLanguage(info.selectedNodes[0].fileExt ?? '') as any);
    }
  }
};

export default CodePreviewCollapse;
