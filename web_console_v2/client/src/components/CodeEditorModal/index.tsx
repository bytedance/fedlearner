import React, { FC, useState, useMemo, useRef, useReducer } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import classNames from 'classnames';

import {
  createOrUpdateAlgorithmProjectFileContent,
  renameAlgorithmProjectFileContent,
  deleteAlgorithmProjectFileContent,
} from 'services/algorithm';

import { Button, Message, Tooltip, Modal, Upload } from '@arco-design/web-react';
import { IconCodeSquare } from '@arco-design/web-react/icon';
import { Resizable } from 're-resizable';
import FileExplorer, {
  FileDataNode,
  FileExplorerExposedRef,
  Key,
  FileData,
  fileExtToIconMap,
} from 'components/FileExplorer';
import { ArrowUpFill, FolderAddFill, FileAddFill, Close, MenuFold } from 'components/IconPark';
import CodeEditor, { Action } from 'components/CodeEditor';
import StateIndicator from 'components/StateIndicator';
import Tab from './Tab';

import { useSubscribe } from 'hooks';
import { ModalProps } from '@arco-design/web-react/es/Modal/interface';
import { Monaco } from '@monaco-editor/react';
import type * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import { UploadItem } from '@arco-design/web-react/es/Upload';
import { FileContent } from 'typings/algorithm';

import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { transformRegexSpecChar, formatLanguage, getJWTHeaders } from 'shared/helpers';
import { buildRelativePath, getFileInfoByFilePath, readAsTextFromFile } from 'shared/file';
import { MixinCommonTransition, MixinSquare, MixinFlexAlignCenter } from 'styles/mixins';
import { getAlgorithmProjectProps, getAlgorithmProps } from 'components/shared';
import { CONSTANTS } from 'shared/constants';
import styles from './index.module.less';

function MixinHeader() {
  return `
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid var(--border-color);
  `;
}

const Layout = styled.main`
  --bg: #fff;
  --font-color: #1d2129;
  --border-color: #e5e8ef;
  --action-button-color: #86909c;
  --action-button-color-hover: #4e5969;
  --tab-header-bg: #f2f3f8;

  --left-width: 272px;

  display: grid;
  grid-template-areas: 'head head' 'left right';
  grid-template-rows: 46px calc(100vh - 46px);
  grid-template-columns: var(--left-width) calc(max(500px, 100vw) - var(--left-width));

  height: 100vh;
  width: 100vw;
  min-width: 500px;
  min-height: 500px;
  background-color: var(--bg);
  overflow: hidden;
`;

const Header = styled.div`
  ${MixinHeader()};
  grid-area: head;
`;
const FileExplorerHeader = styled.div`
  ${MixinHeader()};
  height: 36px;
`;
const TabHeader = styled.div`
  height: 36px;
  width: 100%;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--tab-header-bg);
  overflow-x: auto;
  white-space: nowrap;
`;

const Left = styled(Resizable)`
  position: relative;
  height: 100%;
  grid-area: left;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  z-index: 1; // overlay right layout
  background-color: var(--bg);
  padding-bottom: 40px;

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

const Right = styled.div`
  position: relative;
  height: 100%;
  display: flex;
  grid-area: right;
  flex-direction: column;
  background-color: var(--bg);
`;

const Title = styled.span`
  font-size: 14px;
  font-weight: 500;
  color: var(--font-color);
`;

const ActionContainer = styled.span`
  > button:not(:last-child) {
    margin-right: 8px;
  }
  > span:not(:last-child) {
    margin-right: 8px;
  }
  .arco-upload-trigger {
    display: inline;
  }
  .anticon {
    color: var(--action-button-color);
    cursor: pointer;
    font-size: 18px;
    &:not(:last-child) {
      margin-right: 8px;
    }
    &:hover {
      color: var(--action-button-color-hover);
    }
    &.anticon-close {
      font-size: 14px;
    }
  }
`;

const FoldButton = styled.div`
  ${MixinSquare(24)}
  ${MixinFlexAlignCenter()}

  position:absolute;
  right: 8px;
  bottom: 8px;
  display: inline-flex;
  background-color: rgb(var(--gray-1));
  color: rgb(var(--gray-6));
  border-radius: 2px;
  cursor: pointer;

  &:hover {
    background-color: rgb(var(--gray-2));
  }
`;

export const MIN_FILE_TREE_WIDTH = 220;
export const MAX_FILE_TREE_WIDTH = 600;

const resizeableEnable = {
  right: true,
};

export type BaseCodeEditorProps = {
  /** Algorithm project id / Algorithm id */
  id?: ID;
  /** Modal display title */
  title?: string;
  isReadOnly?: boolean;
  initialFileData?: FileData;
  isAsyncMode?: boolean;
  /** On reset button click, only work in sync mode */
  onReset?: () => void;
  /** On save button click, it will send latest fileData in sync mode */
  onSave?: (fileData: FileData) => void;
  /** On close button click */
  onClose?: () => void;
  getFileTreeList?: () => Promise<any[]>;
  getFile?: (filePath: string) => Promise<any>;
  onFileDataChange?: (fileData: FileData) => void;
  /** Call this fn when they are some file are changed including create/delete/rename/change file content */
  onContentChange?: () => void;
};

export type AsyncBaseCodeEditorProps = Omit<BaseCodeEditorProps, 'id'> &
  Required<Pick<BaseCodeEditorProps, 'id'>>;

export interface FileTab {
  node: FileDataNode;
  model: monaco.editor.ITextModel | null;
}

export type Props = Omit<ModalProps, 'title'> & BaseCodeEditorProps;
export type AsyncProps = Omit<Props, 'id'> & Required<Pick<Props, 'id'>>;
export type AlgorithmProjectFormButtonProps = Omit<AsyncProps, 'width' | 'height'> & {
  /** Container width */
  width?: number | string;
  /** Container height */
  height?: number | string;
};

export const BaseCodeEditor: FC<BaseCodeEditorProps> & {
  AlgorithmProject: FC<AsyncBaseCodeEditorProps>;
  Algorithm: FC<AsyncBaseCodeEditorProps>;
} = ({
  id,
  title = '',
  initialFileData = {},
  isReadOnly = false,
  isAsyncMode = false,
  getFileTreeList,
  getFile,
  onFileDataChange: onFileDataChangeFromProps,
  onContentChange,
  ...restProps
}) => {
  const { t } = useTranslation();

  const [selectedNode, setSelectedNode] = useState<FileDataNode>();
  const [editingNode, setEditingNode] = useState<FileDataNode>();
  const [fileData, setFileData] = useState<FileData>(initialFileData ?? {});
  const [fileTabList, setFileTabList] = useState<FileTab[]>([]);
  const [leftWidth, setLeftWidth] = useState(272);
  const [isLoading, setIsLoading] = useState(false);

  const fileExplorerRef = useRef<FileExplorerExposedRef>(null);
  const tempCodeRef = useRef('');
  const codeEditorInstance = useRef<monaco.editor.IStandaloneCodeEditor>();
  const monacoInstance = useRef<Monaco>();
  const pendingCreateOrFocusTabQueue = useRef<FileDataNode[]>([]);
  const tempLeftWidth = useRef<number | null>(null);
  const [isFocusMode, setIsFocusMode] = useState(false);

  const fileKeyToViewState = useRef<{
    [key: string]: monaco.editor.ICodeEditorViewState | null;
  }>({});

  const [, forceUpdate] = useReducer((x) => x + 1, 0);

  const selectedKeys = useMemo(() => {
    return selectedNode ? [selectedNode.key] : [];
  }, [selectedNode]);

  // subscribe CodeEdiot action(command + s), to save file
  useSubscribe(Action.Save, () => saveEditorCode(), [fileData, editingNode]);

  return (
    <Layout
      style={
        {
          '--left-width': `${leftWidth}px`,
        } as React.CSSProperties
      }
    >
      <Header>
        <Title>{title}</Title>
        <ActionContainer>
          {!isReadOnly && (
            <>
              <Button type="primary" size="small" onClick={onSave}>
                {t('save')}
              </Button>
              {!isAsyncMode && (
                <Button size="small" onClick={onReset}>
                  {t('reset')}
                </Button>
              )}
            </>
          )}
          <Button size="small" icon={<Close />} onClick={onClose} />
        </ActionContainer>
      </Header>
      <Left
        size={{ width: 'var(--left-width)', height: 'auto' }}
        minWidth={MIN_FILE_TREE_WIDTH}
        maxWidth={MAX_FILE_TREE_WIDTH}
        enable={resizeableEnable}
        handleWrapperClass={classNames({
          'resize-bar-wrapper': true,
          resizing: !!tempLeftWidth.current,
        })}
        onResize={(e, direction, ref, d) => {
          // If trigger onResize first time, save prev left width
          if (!tempLeftWidth.current) {
            tempLeftWidth.current = leftWidth;
          }
          let nextLeftWidth = tempLeftWidth.current + d.width;

          if (nextLeftWidth <= MIN_FILE_TREE_WIDTH) {
            nextLeftWidth = MIN_FILE_TREE_WIDTH;
          } else if (nextLeftWidth >= MAX_FILE_TREE_WIDTH) {
            nextLeftWidth = MAX_FILE_TREE_WIDTH;
          }
          setLeftWidth(nextLeftWidth);
        }}
        onResizeStop={(e, direction, ref, d) => {
          // Reset tempLeftWidth
          tempLeftWidth.current = null;
          // Only to refresh handleWrapperClass
          forceUpdate();
        }}
      >
        <FileExplorerHeader>
          <Title>文件列表</Title>
          {!isReadOnly && (
            <ActionContainer>
              <Upload
                className={styles.code_editor_upload}
                disabled={isLoading || isFocusMode}
                name="file"
                showUploadList={false}
                headers={getJWTHeaders()}
                action={`/api/v2/algorithm_projects/${id}/files`}
                onChange={onUploadChange}
                beforeUpload={() => {
                  return isAsyncMode;
                }}
                data={(file) => {
                  const { name } = file;

                  const folderKey = selectedNode
                    ? selectedNode.isFolder
                      ? selectedNode.key
                      : selectedNode.parentKey
                    : '';

                  return {
                    path: folderKey,
                    filename: name,
                  };
                }}
              >
                <Tooltip content={t('upload.label_upload')}>
                  <ArrowUpFill data-testid="btn-upload" />
                </Tooltip>
              </Upload>
              <Tooltip content={t('create_folder_on_root')}>
                <FolderAddFill
                  onClick={onAddFolderOnRoot}
                  data-testid="btn-create-folder-on-root"
                />
              </Tooltip>
              <Tooltip content={t('create_file_on_root')}>
                <FileAddFill onClick={onAddFileOnRoot} data-testid="btn-create-file-on-root" />
              </Tooltip>
            </ActionContainer>
          )}
        </FileExplorerHeader>
        <FileExplorer
          isAsyncMode={isAsyncMode}
          getFileTreeList={getFileTreeList}
          getFile={getFile}
          isLoading={isLoading}
          fileData={fileData}
          selectedKeys={selectedKeys}
          ref={fileExplorerRef}
          isReadOnly={isReadOnly}
          onSelect={onSelect as any}
          onSelectFile={onFileNodeSelect}
          onFileDataChange={onFileDataChange}
          onDeleteFinish={onDeleteFinish}
          onRenameFinish={onRenameFinish}
          onCreateFinish={onCreateFinish}
          onClickRename={onClickRename}
          beforeCreate={beforeCreate}
          beforeRename={beforeRename}
          beforeDelete={beforeDelete}
          onFocusModeChange={onFocusModeChange}
        />
        <FoldButton onClick={onFoldClick}>
          <MenuFold />
        </FoldButton>
      </Left>

      <Right>
        <TabHeader data-testid="tab-list">
          {fileTabList.map((item) => {
            return (
              <Tab
                isActive={editingNode?.key === item.node.key}
                key={item.node.key}
                fileName={String(item.node.label)}
                fullPathFileName={String(item.node.key)}
                icon={
                  fileExtToIconMap[formatLanguage(item.node.fileExt ?? '')]
                    ? fileExtToIconMap[formatLanguage(item.node.fileExt ?? '')]
                    : fileExtToIconMap['default']
                }
                onClick={() => {
                  // prevent select same tab
                  if (item.node.key === selectedNode?.key) {
                    return;
                  }
                  focusTab(item);
                }}
                onClose={() => {
                  onDeleteFinish([item.node.key], item.node.key, true);
                }}
              />
            );
          })}
        </TabHeader>
        <CodeEditor
          theme="light"
          isReadOnly={isReadOnly || isLoading || fileTabList.length === 0}
          onChange={onCodeChange}
          getInstance={getCodeEditorInstance}
        />
      </Right>
    </Layout>
  );

  async function createOrUpdateNodeInBackEnd(
    filePath: string,
    isFolder: boolean,
    code: string = '',
  ) {
    if (!isAsyncMode || !id) return;

    const { parentPath, fileName } = getFileInfoByFilePath(filePath);
    setIsLoading(true);
    try {
      const result = await createOrUpdateAlgorithmProjectFileContent(id, {
        path: parentPath,
        filename: fileName,
        is_directory: isFolder,
        file: code,
      });
      setIsLoading(false);
      return result;
    } catch (error) {
      Message.error(error.message);
      setIsLoading(false);
      return Promise.reject(error);
    }
  }
  async function renameNodeInBackEnd(oldPath: string, newPath: string) {
    if (!isAsyncMode || !id) return;

    setIsLoading(true);
    try {
      const result = await renameAlgorithmProjectFileContent(id, {
        path: oldPath,
        dest: newPath,
      });
      setIsLoading(false);
      return result;
    } catch (error) {
      Message.error(error.message);
      setIsLoading(false);
      return Promise.reject(error);
    }
  }
  async function deleteNodeInBackEnd(filePath: string) {
    if (!isAsyncMode || !id) return;

    setIsLoading(true);
    try {
      const result = await deleteAlgorithmProjectFileContent(id, { path: filePath });
      setIsLoading(false);
      return result;
    } catch (error) {
      Message.error(error.message);
      setIsLoading(false);
      return Promise.reject(error);
    }
  }

  function resetState() {
    tempCodeRef.current = '';
    fileKeyToViewState.current = {};
    // dispose model
    fileTabList.forEach((item) => {
      item.model?.dispose();
    });
    setFileTabList([]);
    setSelectedNode(undefined);
    setEditingNode(undefined);
  }

  function getCodeEditorInstance(editor: monaco.editor.IStandaloneCodeEditor, monaco: Monaco) {
    codeEditorInstance.current = editor;
    monacoInstance.current = monaco;

    // dequeue pending queue
    if (pendingCreateOrFocusTabQueue.current.length > 0) {
      pendingCreateOrFocusTabQueue.current.forEach((node) => createOrFocusTab(node));

      // reset pending queue
      pendingCreateOrFocusTabQueue.current = [];
    }
  }

  function createOrFocusTab(node: FileDataNode) {
    if (!monacoInstance.current || !codeEditorInstance.current) {
      // enqueue pending queue
      pendingCreateOrFocusTabQueue.current.push(node);
      return;
    }
    const monaco = monacoInstance.current;
    const tempUri = monaco.Uri.file(String(node.key));
    let model = monaco.editor.getModel(tempUri);
    // if model not exist create, otherwise replace value (for editor resets).
    if (model === null) {
      model = monaco.editor.createModel(
        node.code ?? '',
        formatLanguage(node.fileExt ?? '') ?? undefined,
        tempUri,
      );

      // add new tab
      setFileTabList((prevState) => [
        ...prevState,
        {
          node,
          model,
        },
      ]);
    }

    // focus editor
    // codeEditorInstance.current?.focus();
    // save editor view state
    if (editingNode) {
      const tempState = codeEditorInstance.current.saveViewState();
      fileKeyToViewState.current[String(editingNode?.key)] = tempState;
    }
    fileKeyToViewState.current[node.key] = null;

    // replace editor model
    codeEditorInstance.current?.setModel(model);

    if (fileKeyToViewState.current[node.key]) {
      codeEditorInstance.current?.restoreViewState(fileKeyToViewState.current[node.key]!);
    }
  }

  async function saveEditorCode(node?: FileDataNode) {
    // save prev tempCodeRef
    if (editingNode) {
      const tempCode = tempCodeRef.current;
      try {
        if (isAsyncMode) {
          // Save code in Back-end
          await createOrUpdateNodeInBackEnd(
            String(editingNode.key),
            Boolean(editingNode.isFolder),
            tempCode,
          );
        }

        setFileData((prevState) => {
          return {
            ...prevState,
            [editingNode.key]: tempCode,
          };
        });
        onFileDataChangeFromProps?.({ ...fileData, [editingNode.key]: tempCode });
        onContentChange?.();
      } catch (error) {
        // Do nothing
      }
    }
    if (node) {
      tempCodeRef.current = fileData[String(node.key)] || node.code || '';
    }
  }

  function focusTab(tab: FileTab, isSaveCode = true) {
    if (!monacoInstance.current || !codeEditorInstance.current) {
      return;
    }

    if (isSaveCode) {
      saveEditorCode(tab.node);
    } else {
      tempCodeRef.current = fileData[String(tab.node.key)] || tab.node.code || '';
    }

    // focus editor
    // codeEditorInstance.current?.focus();
    const tempState = codeEditorInstance.current.saveViewState();
    fileKeyToViewState.current[String(editingNode?.key)] = tempState;

    setSelectedNode(tab.node);
    setEditingNode(tab.node);
    codeEditorInstance.current?.setModel(tab.model);

    if (fileKeyToViewState.current[tab.node.key]) {
      codeEditorInstance.current?.restoreViewState(fileKeyToViewState.current[tab.node.key]!);
    }
  }

  function onDeleteFinish(deleteKeys: Key[], firstDeleteKey: Key, isTabClick = false) {
    const newFileTabList: FileTab[] = [];
    fileTabList.forEach((item) => {
      if (deleteKeys.includes(item.node.key)) {
        // dispose model
        item.model?.dispose();

        // clear fileKeyToViewState
        delete fileKeyToViewState.current[item.node.key];
      } else {
        newFileTabList.push(item);
      }
    });

    // delete active node
    if (selectedNode && deleteKeys.includes(selectedNode.key)) {
      setSelectedNode(undefined);
    }
    if (editingNode && deleteKeys.includes(editingNode.key)) {
      setEditingNode(undefined);
      // default select first tab
      if (newFileTabList.length > 0) {
        // must clear node state, otherwise saveEditorCode will create extra same node
        focusTab(newFileTabList[0], false);
      }
    }

    setFileTabList(newFileTabList);

    if (newFileTabList.length === 0) {
      resetState();
    }
    if (!isTabClick) {
      onContentChange?.();
    }
  }
  async function onRenameFinish(node: FileDataNode, oldKey: Key, newKey: Key) {
    onContentChange?.();

    if (!node.isFolder) {
      // rename file node
      if (selectedNode?.key === oldKey) {
        // must clear node state, otherwise saveEditorCode will create extra same node
        setSelectedNode(undefined);
        setEditingNode(undefined);
      }

      const oldTabIndex = fileTabList.findIndex((item) => item.node.key === oldKey);

      if (oldTabIndex === -1) {
        return;
      }
      const { model: oldModel } = fileTabList[oldTabIndex];

      // rename fileKeyToViewState
      const oldViewState = fileKeyToViewState.current[String(oldKey)];
      fileKeyToViewState.current[String(newKey)] = oldViewState;
      delete fileKeyToViewState.current[String(oldKey)];

      // dispose oldModel
      oldModel?.dispose();

      // TODO: Find a good way to replace oldTab to newTab, no just only delete oldTab
      setFileTabList([...fileTabList.slice(0, oldTabIndex), ...fileTabList.slice(oldTabIndex + 1)]);
    } else {
      // rename folder node
      const allOldFileKey: Key[] = [];

      const regx = new RegExp(`^${transformRegexSpecChar(String(oldKey))}`); // prefix originKey
      // find all file node key under this folder
      Object.keys(fileData).forEach((key) => {
        if (!!key.match(regx)) {
          allOldFileKey.push(key);
        }
      });

      if (allOldFileKey.includes(String(selectedNode?.key))) {
        // must clear node state, otherwise saveEditorCode will create extra same node
        setSelectedNode(undefined);
        setEditingNode(undefined);
      }

      // rename fileKeyToViewState
      const filteredFileTabList = fileTabList.filter((item) => {
        const { node: oldNode, model: oldModel } = item;
        if (allOldFileKey.includes(oldNode.key)) {
          const oldViewState = fileKeyToViewState.current[String(oldNode.key)];
          const tnewKey = String(oldNode.key).replace(regx, String(newKey));

          fileKeyToViewState.current[String(tnewKey)] = oldViewState;
          delete fileKeyToViewState.current[String(oldNode.key)];

          // dispose oldModel
          oldModel?.dispose();

          // delete this tab
          return false;
        }
        // reserve this tab
        return true;
      });
      setFileTabList(filteredFileTabList);
    }
  }
  function onCreateFinish(path: Key, isFolder: boolean) {
    onContentChange?.();
  }
  function onClickRename(node: FileDataNode) {
    saveEditorCode();
  }
  function onFocusModeChange(focusMode: boolean) {
    setIsFocusMode(focusMode);
  }

  function onCodeChange(val?: string) {
    // store temp code
    tempCodeRef.current = val ?? '';
  }
  function onFileDataChange(fileData: FileData) {
    setFileData(fileData);
    onFileDataChangeFromProps?.(fileData);
  }
  function onFileNodeSelect(filePath: Key, fileContent: string, node: FileDataNode) {
    // prevent select same node
    if (node.key === selectedNode?.key) {
      return;
    }
    setSelectedNode(node);
    saveEditorCode(node);
    setEditingNode(node);
    createOrFocusTab(node);
  }
  function onSelect(
    selectedKeys: Key[],
    info: {
      selected: boolean;
      selectedNodes: FileDataNode[];
      node: FileDataNode;
      e: Event;
    },
  ) {
    // folder or file
    if (info.selected && info.selectedNodes && info.selectedNodes[0]) {
      const currentNode = info.selectedNodes[0];
      // prevent select same node
      if (currentNode.key === selectedNode?.key) {
        return;
      }

      setSelectedNode(currentNode);
    }
  }

  async function onUploadChange(fileList: UploadItem[], info: UploadItem) {
    const { status, response, name } = info;
    switch (status) {
      case 'done':
        const resData: Omit<FileContent, 'content'> = (response as any).data;
        const fileKey = buildRelativePath(resData);

        // Set <FileExplorer/>'s inner filePathToIsReadMap, so it will fetch file content API when select this upload file
        fileExplorerRef.current?.setFilePathToIsReadMap({
          [fileKey]: false,
        });

        // Display node in file explorer
        setFileData((prevState) => {
          return {
            ...prevState,
            [fileKey]: '',
          };
        });
        onFileDataChangeFromProps?.({
          ...fileData,
          [(response as any).data.path]: (response as any).data.content,
        });
        onContentChange?.();
        setIsLoading(false);
        break;
      case 'error':
        Message.error(t('upload.msg_upload_fail', { fileName: info.name }));
        setIsLoading(false);
        break;
      case 'uploading':
        setIsLoading(true);
        break;
      // When beforeUpload return false, status will be undefined.
      // In this case, isAsyncMode = false, so read file content locally
      case undefined:
        // const template = await readAsJSONFromFile(info.file as any);
        const code = await readAsTextFromFile(info.originFile as any);

        const folderKey = selectedNode
          ? selectedNode.isFolder
            ? selectedNode.key
            : selectedNode.parentKey
          : '';

        const path = `${folderKey ? `${folderKey}/` : ''}${name}`;
        setFileData((prevState) => {
          return {
            ...prevState,
            [path]: code,
          };
        });
        onFileDataChangeFromProps?.({ ...fileData, [path]: code });
        onContentChange?.();

        break;
      default:
        break;
    }
  }
  function onAddFolderOnRoot() {
    if (isLoading || isFocusMode) return;
    fileExplorerRef.current?.createFileOrFolder(undefined, false);
  }
  function onAddFileOnRoot() {
    if (isLoading || isFocusMode) return;

    fileExplorerRef.current?.createFileOrFolder(undefined, true);
  }
  function onFoldClick() {
    setLeftWidth(MIN_FILE_TREE_WIDTH);
  }

  async function onSave() {
    if (isAsyncMode) {
      await saveEditorCode();
      Message.success(t('algorithm_management.form_code_changed'));
    } else {
      let finalFileData = fileData;
      if (editingNode) {
        const tempCode = tempCodeRef.current;
        finalFileData = {
          ...fileData,
          [editingNode.key]: tempCode,
        };
        setFileData(finalFileData);
        onFileDataChangeFromProps?.(finalFileData);
      }
      Message.success(t('algorithm_management.form_code_changed'));
      restProps.onSave?.(finalFileData);
    }
  }
  function onReset() {
    if (isAsyncMode) return;
    setFileData(initialFileData);
    onFileDataChangeFromProps?.(initialFileData);

    resetState();

    restProps.onReset?.();
  }
  async function onClose() {
    if (restProps.onClose) {
      // Clear all code editor model info in memory
      // If no clear, it will effect create <Tab/>
      resetState();
      restProps.onClose();
    }
  }

  async function beforeCreate(node: FileDataNode, key: Key, isFolder: boolean) {
    try {
      if (isAsyncMode) {
        // Create new file/folder when API response success
        const result = await createOrUpdateNodeInBackEnd(String(key), isFolder);
        const fileKey = result && result.data ? buildRelativePath(result.data) : key;
        return String(fileKey);
      }
    } catch (error) {
      return false; // return false to prevent create file/folder
    }
    return true;
  }
  async function beforeRename(node: FileDataNode, oldKey: Key, newKey: Key, isFolder: boolean) {
    try {
      if (isAsyncMode) {
        // Save code in Back-end if this node is editingNode
        if (editingNode?.key === node.key) {
          // Save code in Back-end
          await createOrUpdateNodeInBackEnd(
            String(editingNode.key),
            Boolean(editingNode.isFolder),
            tempCodeRef.current || '',
          );
        }
        // Rename node in Back-end
        await renameNodeInBackEnd(String(oldKey), String(newKey));
      }
    } catch (error) {
      return false; // return false to prevent rename file/folder
    }
    return true;
  }
  async function beforeDelete(key: Key, isFolder: boolean) {
    try {
      if (isAsyncMode) {
        await deleteNodeInBackEnd(String(key));
      }
    } catch (error) {
      return false; // return false to prevent delete file/folder
    }
    return true;
  }
};

const _BaseCodeEditorWithAlgorithmProjectAPI: FC<AsyncBaseCodeEditorProps> = ({
  id,
  ...restProps
}) => {
  return <BaseCodeEditor {...getAlgorithmProjectProps({ id: id! })} {...restProps} />;
};

const _BaseCodeEditorWithAlgorithmAPI: FC<AsyncBaseCodeEditorProps> = ({ id, ...restProps }) => {
  return <BaseCodeEditor {...getAlgorithmProps({ id: id! })} {...restProps} />;
};

export const CodeEditorModal: FC<Props> & {
  AlgorithmProject: FC<AsyncProps>;
  Algorithm: FC<AsyncProps>;
  AlgorithmProjectFormButton: FC<AlgorithmProjectFormButtonProps>;
} = ({
  id,
  isAsyncMode = false,
  visible = false,
  title = CONSTANTS.EMPTY_PLACEHOLDER,
  initialFileData,
  isReadOnly = false,
  onReset = () => {},
  onSave = () => {},
  onClose = () => {},
  getFileTreeList,
  getFile,
  onFileDataChange,
  onContentChange,
  ...resetProps
}) => {
  return (
    <Modal
      visible={visible}
      style={{ width: '100vw', zIndex: Z_INDEX_GREATER_THAN_HEADER }}
      closable={false}
      mask={false}
      maskClosable={false}
      wrapClassName="global-code-editor-model-wrapper"
      unmountOnExit={true}
      footer={null}
      className={styles.code_editor_model_wrapper}
      {...resetProps}
    >
      <BaseCodeEditor
        initialFileData={initialFileData}
        title={title}
        isReadOnly={isReadOnly}
        onReset={onReset}
        onSave={onSave}
        onClose={onClose}
        id={id}
        isAsyncMode={isAsyncMode}
        getFileTreeList={getFileTreeList}
        getFile={getFile}
        onFileDataChange={onFileDataChange}
        onContentChange={onContentChange}
      />
    </Modal>
  );
};

const _CodeEditorModalWithAlgorithmProjectAPI: FC<AsyncProps> = ({ id, ...restProps }) => {
  return <CodeEditorModal {...getAlgorithmProjectProps({ id: id! })} {...restProps} />;
};

const _CodeEditorModalWithAlgorithmAPI: FC<AsyncProps> = ({ id, ...restProps }) => {
  return <CodeEditorModal {...getAlgorithmProps({ id: id! })} {...restProps} />;
};

const FormButtonContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 24px 0;
  border: 1px dashed var(--lineColor);
  border-radius: 2px;
  background: rgb(var(--gray-2));
  cursor: pointer;
  ${MixinCommonTransition('border-color')}

  &:hover {
    border-color: var(--primaryColor);
  }
`;
const FormButtonTitle = styled.div`
  color: var(--textColorStrong);
  font-weight: 500;
  font-size: 16px;
  margin: 14px 0 4px;
`;
const FormButtonTip = styled.span`
  display: inline-block;
  color: var(--textColorSecondary);
  font-size: 12px;
`;
export const AlgorithmProjectFormButton: FC<AlgorithmProjectFormButtonProps> = ({
  id,
  width = '100%',
  height = 140,
  ...restProps
}) => {
  const [isShowCodeEditor, setIsShowCodeEditor] = useState(false);
  const [isEdited, setIsEdited] = useState(false);

  return (
    <>
      <FormButtonContainer
        style={{
          width,
          height,
        }}
        onClick={() => {
          setIsShowCodeEditor(true);
        }}
      >
        <IconCodeSquare />
        <FormButtonTitle>代码编辑器</FormButtonTitle>
        <div>
          <StateIndicator
            type={isEdited ? 'success' : 'default'}
            text={isEdited ? '已保存' : '未编辑'}
            tag={true}
          />
          <FormButtonTip> {isEdited ? '更改内容已在后台保存' : '点击进入代码编辑器'}</FormButtonTip>
        </div>
      </FormButtonContainer>
      <CodeEditorModal
        visible={isShowCodeEditor}
        onClose={() => {
          setIsShowCodeEditor(false);
        }}
        onContentChange={() => {
          if (!isEdited) {
            setIsEdited(true);
          }
        }}
        {...getAlgorithmProjectProps({ id: id! })}
        {...restProps}
      />
    </>
  );
};

BaseCodeEditor.AlgorithmProject = _BaseCodeEditorWithAlgorithmProjectAPI;
BaseCodeEditor.Algorithm = _BaseCodeEditorWithAlgorithmAPI;
CodeEditorModal.AlgorithmProject = _CodeEditorModalWithAlgorithmProjectAPI;
CodeEditorModal.Algorithm = _CodeEditorModalWithAlgorithmAPI;
CodeEditorModal.AlgorithmProjectFormButton = AlgorithmProjectFormButton;

export default CodeEditorModal;
