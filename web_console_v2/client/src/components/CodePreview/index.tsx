/* istanbul ignore file */

import React, { FC, useState } from 'react';
import styled from 'styled-components';
import classNames from 'classnames';

import { MixinCommonTransition } from 'styles/mixins';
import { formatLanguage } from 'shared/helpers';

import { Resizable } from 're-resizable';
import CodeEditor from 'components/CodeEditor';
import FileExplorer, { FileDataNode } from 'components/FileExplorer';
import {
  getAlgorithmProjectProps,
  getAlgorithmProps,
  getPeerAlgorithmProps,
  getPendingAlgorithmProps,
} from 'components/shared';

const Container = styled.div`
  display: flex;
  flex: 1;
  border: 1px solid var(--lineColor);

  .resize-bar-wrapper {
    &.resizing > div,
    > div:hover {
      ${MixinCommonTransition('background-color')}
      padding:0 3px;
      background-clip: content-box;
      background-color: var(--primaryColor);
    }
  }
`;

const StyledResizable = styled(Resizable)`
  position: relative;
  padding: 12px 0 0 0;
  overflow: hidden;
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

export type Props = {
  /** Algorithm project id / Algorithm id */
  id?: ID;
  isAsyncMode?: boolean;
  getFileTreeList?: () => Promise<any[]>;
  getFile?: (filePath: string) => Promise<any>;
  /** Container height */
  height?: number | string;
  /** Default display value. Only work on sync mode, it isn't work on async mode */
  fileData?: { [filePath: string]: string };
  isLoading?: boolean;
};

export type AsyncProps = Omit<Props, 'od'> & Required<Pick<Props, 'id'>>;

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

const CodePreview: FC<Props> & {
  Algorithm: FC<AsyncProps>;
  AlgorithmProject: FC<AsyncProps>;
  PendingAlgorithm: FC<AsyncProps & { projId: ID }>;
  PeerAlgorithm: FC<AsyncProps & { participantId: ID; projId: ID; uuid: ID }>;
} = ({ id, fileData, height = 480, isLoading, isAsyncMode = false, getFileTreeList, getFile }) => {
  const [currentCode, setCurrentCode] = useState('');
  const [currentLanguage, setCurrentLanguage] = useState<
    'json' | 'python' | 'javascript' | 'java' | 'go'
  >('python');

  const [isResizing, setIsResizing] = useState(false);

  return (
    <Container
      style={{
        height,
      }}
    >
      <StyledResizable
        defaultSize={resizeableDefaultSize}
        minWidth={MIN_FILE_TREE_WIDTH}
        maxWidth={MAX_FILE_TREE_WIDTH}
        enable={resizeableEnable}
        handleWrapperClass={classNames({
          'resize-bar-wrapper': true,
          resizing: isResizing,
        })}
        onResize={(e, direction, ref, d) => {
          if (isResizing) return;
          setIsResizing(true);
        }}
        onResizeStop={(e, direction, ref, d) => {
          setIsResizing(false);
        }}
      >
        <FileExplorer
          style={{ height: '100%' }}
          isAsyncMode={isAsyncMode}
          isReadOnly={true}
          isLoading={isLoading}
          fileData={isAsyncMode ? undefined : fileData}
          getFileTreeList={getFileTreeList}
          getFile={getFile}
          onSelectFile={onFileNodeSelect}
        />
      </StyledResizable>
      <Right>
        <CodeEditor isReadOnly={true} language={currentLanguage} value={currentCode} theme="grey" />
      </Right>
    </Container>
  );

  function onFileNodeSelect(filePath: Key, fileContent: string, node: FileDataNode) {
    setCurrentCode(fileContent ?? '');
    setCurrentLanguage(formatLanguage(node.fileExt ?? '') as any);
  }
};

const _WithAlgorithmProjectAPI: FC<AsyncProps> = ({ id, ...restProps }) => {
  return <CodePreview {...getAlgorithmProjectProps({ id: id! })} {...restProps} />;
};

const _WithAlgorithmAPI: FC<AsyncProps> = ({ id, ...restProps }) => {
  return <CodePreview {...getAlgorithmProps({ id: id! })} {...restProps} />;
};

const _WithPendingAlgorithmAPI: FC<AsyncProps & { projId: ID }> = ({
  projId,
  id,
  ...restProps
}) => {
  return <CodePreview {...getPendingAlgorithmProps({ projId: projId!, id: id! })} {...restProps} />;
};

const _WithPeerAlgorithmAPI: FC<AsyncProps & { participantId: ID; projId: ID; uuid: ID }> = ({
  id,
  participantId,
  projId,
  uuid,
  ...restProps
}) => {
  return (
    <CodePreview
      {...getPeerAlgorithmProps({
        id: id!,
        participantId: participantId,
        projId: projId,
        uuid: uuid,
      })}
      {...restProps}
    />
  );
};

CodePreview.AlgorithmProject = _WithAlgorithmProjectAPI;
CodePreview.Algorithm = _WithAlgorithmAPI;
CodePreview.PendingAlgorithm = _WithPendingAlgorithmAPI;
CodePreview.PeerAlgorithm = _WithPeerAlgorithmAPI;

export default CodePreview;
