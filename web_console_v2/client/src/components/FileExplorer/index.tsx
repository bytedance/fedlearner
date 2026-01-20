import React, {
  ForwardRefRenderFunction,
  useMemo,
  useState,
  useEffect,
  useRef,
  useImperativeHandle,
  forwardRef,
} from 'react';
import styled from 'styled-components';
import i18n from 'i18n';
import { useMount } from 'react-use';
import classNames from 'classnames';
import { record } from 'shared/object';
import { Spin, Message, Tooltip, Form, Input, Tree } from '@arco-design/web-react';
import NoResult from 'components/NoResult';
import {
  EditNoUnderline,
  Check,
  Close,
  FolderAddFill,
  FileAddFill,
  ArrowFillDown,
  ArrowFillRight,
} from 'components/IconPark';
import MoreActions from 'components/MoreActions';

import { TreeProps, TreeNodeProps } from '@arco-design/web-react/es/Tree';
import { FormItemProps } from '@arco-design/web-react/es/Form/interface';
import {
  transformRegexSpecChar,
  giveWeakRandomKey,
  dfs,
  formatTreeData,
  getFirstFileNode,
  fileExtToIconMap as fileExtToIconMapOrigin,
  formatFileTreeNodeListToFileData,
} from 'shared/helpers';
import './index.less';
const TreeNode = Tree.Node;

export const fileExtToIconMap = fileExtToIconMapOrigin;

export type Key = string;

export type FileDataNode = TreeNodeProps & {
  key: string;
  code?: string | null;
  fileExt?: string;
  parentKey?: Key;
  label?: string;
  children?: FileDataNode[];
  isFolder?: boolean;
};

export type FileData = { [filePath: string]: string | null };
export type FilePathToIsReadMap = { [filePath: string]: boolean };

export type Props = {
  fileData?: FileData;
  getFileTreeList?: () => Promise<any[]>;
  getFile?: (filePath: string) => Promise<any>;
  formatFileTreeListToFileData?: (data: any[]) => FileData;
  isAsyncMode?: boolean;
  isLoading?: boolean;
  isAutoSelectFirstFile?: boolean;
  isReadOnly?: boolean;
  isShowNodeTooltip?: boolean;
  isExpandAll?: boolean;
  onFileDataChange?: (fileData: FileData) => void;
  onDeleteFinish?: (keys: Key[], firstKey: Key) => void;
  onRenameFinish?: (node: FileDataNode, oldKey: Key, newKey: Key) => void;
  onCreateFinish?: (key: Key, isFolder: boolean) => void;
  onSelectFile?: (filePath: Key, fileContent: string, node: FileDataNode) => void;
  onClickRename?: (node: FileDataNode) => void;
  /**
   * When beforeCreate return false or Promise that is resolved false, don't create node
   */
  beforeCreate?: (
    node: FileDataNode,
    key: Key,
    isFolder: boolean,
  ) => boolean | Promise<boolean | string>;
  /**
   * When beforeRename return false or Promise that is resolved false, don't rename node
   */
  beforeRename?: (
    node: FileDataNode,
    oldKey: Key,
    newKey: Key,
    isFolder: boolean,
  ) => boolean | Promise<boolean | string>;
  /**
   * When beforeDelete return false or Promise that is resolved false, don't delete node
   */
  beforeDelete?: (key: Key, isFolder: boolean) => boolean | Promise<boolean>;
  onFocusModeChange?: (isFocusMode: boolean) => void;
} & Partial<TreeProps>;

export type FileExplorerExposedRef = {
  getFileData: () => FileData;
  createFileOrFolder: (node?: FileDataNode, isFile?: boolean) => void;
  setFilePathToIsReadMap: (filePathToIsReadMap: FilePathToIsReadMap) => void;
};

// TODO:There are some dependencies on properties defined by this component that will be removed later
const StyledTreeNode = styled(TreeNode)<{
  code?: string | null;
  fileExt?: string;
  parentKey?: Key;
  label?: string;
  isFolder?: boolean;
}>``;

const FileExplorer: ForwardRefRenderFunction<FileExplorerExposedRef, Props> = (
  {
    fileData,
    getFileTreeList,
    getFile,
    formatFileTreeListToFileData = formatFileTreeNodeListToFileData,
    isAsyncMode = false,
    isLoading: isLoadingFromProps = false,
    isReadOnly = false,
    isShowNodeTooltip = true,
    isAutoSelectFirstFile = true,
    isExpandAll = true,
    onFileDataChange,
    onSelect: onSelectFromProps,
    onSelectFile,
    onDeleteFinish,
    onRenameFinish,
    onCreateFinish,
    onClickRename,
    beforeCreate,
    beforeRename,
    beforeDelete,
    selectedKeys: selectedKeysFromProps,
    expandedKeys: expandedKeysFromProps,
    onFocusModeChange,
    ...restProps
  },
  parentRef,
) => {
  const [tempFileData, setTempFileData] = useState<FileData>(fileData || {});
  const [focusKey, setFocusKey] = useState<Key | null>();
  const [isCreating, setIsCreating] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Array<Key>>([]);
  const [expandedKeys, setExpandedKeys] = useState<Array<Key>>([]);
  const [validateObj, setValidateObj] = useState<{
    validateStatus: FormItemProps['validateStatus'];
    help?: string;
  }>({
    validateStatus: undefined,
    help: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const isDeleteButtonClick = useRef(false);
  const isExpandedAll = useRef(false);
  const isAlreadySelectFirstNode = useRef(false);
  const isAlreadyFetchedFileTreeList = useRef(false);
  const inputRef = useRef<any>(null);
  // TODO: when to clear cache?
  const filePathToIsReadMap = useRef<FilePathToIsReadMap>({});

  // sync fileData
  useEffect(() => {
    if (fileData) {
      setTempFileData((prevState) => fileData);
    }
  }, [fileData]);
  useEffect(() => {
    if (selectedKeysFromProps) {
      setSelectedKeys((prevState) => selectedKeysFromProps);
    }
  }, [selectedKeysFromProps]);
  useEffect(() => {
    if (expandedKeysFromProps) {
      setExpandedKeys((prevState) => expandedKeysFromProps);
    }
  }, [expandedKeysFromProps]);
  useEffect(() => {
    onFocusModeChange?.(Boolean(focusKey));
  }, [focusKey, onFocusModeChange]);

  // Fetch file tree data
  useMount(() => {
    if (!isAsyncMode || !getFileTreeList) return;

    filePathToIsReadMap.current = {};

    setIsLoading(true);
    getFileTreeList()
      .then((data) => {
        const tempFileData = formatFileTreeListToFileData(data || []) || {};
        // If there is no file data, isAutoSelectFirstFile will be invalid
        if (data.length === 0) {
          isAlreadySelectFirstNode.current = true;
        }

        // Store filePathToIsReadMap cache
        filePathToIsReadMap.current = record(tempFileData, false);
        setTempFileData((prevState) => tempFileData);
        setIsLoading(false);

        isAlreadyFetchedFileTreeList.current = true;
      })
      .catch((error) => {
        setIsLoading(false);
        Message.error(error.message);
        // If there is no file data, isAutoSelectFirstFile will be invalid
        isAlreadySelectFirstNode.current = true;
        isAlreadyFetchedFileTreeList.current = true;
      });
  });

  const formattedTreeData = useMemo(() => formatTreeData(tempFileData), [tempFileData]);

  // Auto select first node in synchronous mode
  useMount(() => {
    if (isAsyncMode || !isAutoSelectFirstFile) return;

    selectFirstFileNode(formattedTreeData);
  });
  // Auto select first node in asynchronous mode (after async tree data loaded)
  useEffect(() => {
    if (!isAsyncMode || !isAutoSelectFirstFile || isAlreadySelectFirstNode.current) return;

    selectFirstFileNode(formattedTreeData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAsyncMode, isAutoSelectFirstFile, formattedTreeData]);

  // default expand all folder
  useEffect(() => {
    if (isExpandedAll.current || !formattedTreeData || formattedTreeData.length === 0) {
      return;
    }
    // search all folder node
    const allFolderNode = dfs<FileDataNode>(
      { key: '', parentKey: '', children: formattedTreeData },
      (node) => {
        if (node.isFolder && node.key) {
          return true;
        }
        return false;
      },
    );

    // get all folder key
    if (isExpandAll) {
      setExpandedKeys(allFolderNode.map((item) => item.key));
    }
    isExpandedAll.current = true;
  }, [isExpandAll, isExpandedAll, formattedTreeData]);

  useImperativeHandle(parentRef, () => {
    return {
      getFileData: () => tempFileData,
      createFileOrFolder: onCreateFile,
      setFilePathToIsReadMap,
    };
  });

  if (!formattedTreeData || formattedTreeData.length === 0) {
    return (
      <Spin className={'file-export-wrapper'} loading={isLoadingFromProps || isLoading}>
        <NoResult.NoData />
      </Spin>
    );
  }

  return (
    <Spin className={'file-export-wrapper'} loading={isLoadingFromProps || isLoading}>
      <Tree
        className={`file-directory-tree ${!!focusKey ? 'file-directory-tree-isFocusMode' : ''}`}
        showLine={false}
        autoExpandParent={true}
        blockNode={true}
        size="small"
        selectedKeys={selectedKeys}
        expandedKeys={expandedKeys}
        onSelect={onSelect as any}
        onExpand={onExpand}
        {...restProps}
      >
        {renderTreeNode(formattedTreeData)}
      </Tree>
    </Spin>
  );

  function renderFileTreeNode(node: FileDataNode) {
    const Icon = typeof node.icon === 'function' ? node.icon({ ...restProps }) : node.icon;

    const isFocus = focusKey === node.key;
    return (
      <div className="file-node-content-container">
        {Icon && <span className="file-icon-container">{Icon}</span>}
        {isFocus && !isReadOnly ? (
          <Form.Item {...validateObj} hasFeedback>
            <Input
              style={{
                padding: 0,
              }}
              ref={inputRef}
              autoFocus
              defaultValue={isCreating ? '' : (node.title as string) || ''}
              onChange={(value: string) => {
                isValidateName(value, node);
              }}
              onBlur={(event) => {
                // actual: onBlur => onClick
                // expect: onCick => onBlur
                // in isFocus mode, when click create or delete button, input blur event will trigger first
                // so use setTimeout + local ref flag to change trigger order
                setTimeout(() => {
                  if (!isDeleteButtonClick.current) {
                    onInputBlur(event, node);
                  } else {
                    resetState();
                  }
                }, 100);
              }}
              onKeyDown={(event: any) => {
                onInputKeyPress(event, node);
              }}
              data-testid={`input-${node.key}`}
            />
          </Form.Item>
        ) : isShowNodeTooltip ? (
          <Tooltip content={node.title || ''} position="lb">
            <span className="file-export-node-name" data-testid={node.key}>
              {node.title}
            </span>
          </Tooltip>
        ) : (
          <span className="file-export-node-name" data-testid={node.key}>
            {node.title}
          </span>
        )}
        {!isReadOnly && (
          <span
            className="file-action-list-container"
            style={isFocus ? { visibility: 'visible' } : undefined}
            data-testid={`action-list-container-${node.key}`}
          >
            {isFocus ? (
              <>
                <Tooltip content={i18n.t('create')}>
                  <Check
                    style={{ margin: '0 8px' }}
                    onClick={(event) => {
                      event.stopPropagation();
                      // don't do sth, only trigger input blur event
                    }}
                    data-testid={`btn-ok-${node.key}`}
                  />
                </Tooltip>
                <Tooltip content={'删除'}>
                  <Close
                    onClick={(event) => {
                      event.stopPropagation();
                      // set local ref flag
                      isDeleteButtonClick.current = true;
                      onDeleteFile(node, true);
                    }}
                    data-testid={`btn-delete-${node.key}`}
                  />
                </Tooltip>
              </>
            ) : (
              <>
                <Tooltip content={'编辑'}>
                  <EditNoUnderline
                    onClick={(event) => {
                      event.stopPropagation();
                      onEditFile(node);
                    }}
                    data-testid={`btn-edit-${node.key}`}
                  />
                </Tooltip>
                <MoreActions
                  zIndex={9999}
                  actionList={[
                    {
                      label: '删除',
                      onClick: () => onDeleteFile(node),
                      testId: `btn-more-acitons-delete-${node.key}`,
                    },
                  ]}
                />
              </>
            )}
          </span>
        )}
      </div>
    );
  }
  function renderFolderTreeNode(node: FileDataNode) {
    const isFocus = focusKey === node.key;
    const isExpanded = expandedKeys.includes(node.key);
    return (
      <div className="file-node-content-container">
        <span className="file-icon-container">
          {isExpanded ? <ArrowFillDown /> : <ArrowFillRight />}
        </span>
        {isFocus && !isReadOnly ? (
          <Form.Item {...validateObj} hasFeedback>
            <Input
              style={{
                padding: 0,
              }}
              ref={inputRef}
              autoFocus
              defaultValue={isCreating ? '' : (node.title as string) || ''}
              onChange={(value: string) => {
                isValidateName(value, node);
              }}
              onBlur={(event) => {
                onInputBlur(event, node);
              }}
              onKeyDown={(event: any) => {
                onInputKeyPress(event, node);
              }}
              data-testid={`input-${node.key}`}
            />
          </Form.Item>
        ) : isShowNodeTooltip ? (
          <Tooltip content={node.title || ''} position="tl">
            <span className="file-export-node-name" data-testid={node.key}>
              {node.title}
            </span>
          </Tooltip>
        ) : (
          <span className="file-export-node-name" data-testid={node.key}>
            {node.title}
          </span>
        )}

        {!isReadOnly && (
          <span
            className="file-action-list-container"
            style={isFocus ? { visibility: 'visible' } : undefined}
            data-testid={`action-list-container-${node.key}`}
          >
            {isFocus ? (
              <>
                <Tooltip content={i18n.t('create')}>
                  <Check
                    style={{ margin: '0 8px' }}
                    onClick={(event) => {
                      event.stopPropagation();
                      // don't do sth, only trigger input blur event
                    }}
                    data-testid={`btn-ok-${node.key}`}
                  />
                </Tooltip>
                <Tooltip content={'删除'}>
                  <Close
                    onClick={(event) => {
                      event.stopPropagation();
                      // set local ref flag
                      isDeleteButtonClick.current = true;
                      onDeleteFile(node, true);
                    }}
                    data-testid={`btn-delete-${node.key}`}
                  />
                </Tooltip>
              </>
            ) : (
              <>
                <Tooltip content={'编辑'}>
                  <EditNoUnderline
                    onClick={(event) => {
                      event.stopPropagation();
                      onEditFile(node);
                    }}
                    data-testid={`btn-edit-${node.key}`}
                  />
                </Tooltip>
                <Tooltip content={i18n.t('create_folder')}>
                  <FolderAddFill
                    style={{ marginLeft: 4 }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onCreateFile(node, false);
                    }}
                    data-testid={`btn-create-folder-${node.key}`}
                  />
                </Tooltip>
                <Tooltip content={i18n.t('create_file')}>
                  <FileAddFill
                    style={{ marginLeft: 4 }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onCreateFile(node, true);
                    }}
                    data-testid={`btn-create-file-${node.key}`}
                  />
                </Tooltip>
                <MoreActions
                  zIndex={9999}
                  actionList={[
                    {
                      label: '删除',
                      onClick: () => onDeleteFile(node),
                      testId: `btn-more-acitons-delete-${node.key}`,
                    },
                  ]}
                />
              </>
            )}
          </span>
        )}
      </div>
    );
  }
  function renderTreeNode(treeList: FileDataNode[]) {
    return treeList.map((item) => {
      const isFocus = focusKey === item.key;
      const isSelected = selectedKeys.includes(item.key) && item.isLeaf;
      return (
        <StyledTreeNode
          key={item.key}
          parentKey={item.parentKey}
          title={!item.isFolder ? renderFileTreeNode(item) : renderFolderTreeNode(item)}
          isLeaf={item.isLeaf}
          isFolder={item.isFolder}
          code={item.code}
          fileExt={item.fileExt}
          label={String(item.title)}
          data-key={item.key}
          data-testid={item.key}
          icons={{
            switcherIcon: null,
          }}
          className={classNames({
            'is-focus-mode': !!focusKey,
            'is-focus-node': isFocus,
            'is-not-focus-node': !isFocus,
            'folder-selected': isSelected,
          })}
        >
          {renderTreeNode(item.children || [])}
        </StyledTreeNode>
      );
    });
  }

  function setFileData(fileData: FileData) {
    setTempFileData(fileData);
    onFileDataChange?.(fileData);
  }
  function setFilePathToIsReadMap(finalFilePathToIsReadMap: FilePathToIsReadMap) {
    filePathToIsReadMap.current = { ...filePathToIsReadMap.current, ...finalFilePathToIsReadMap };
  }
  async function renameFileOrFolder(node: FileDataNode, renameKey: string) {
    const isFile = !node.isFolder;
    const originKey = String(node.key);

    if (
      (isFile && !Object.prototype.hasOwnProperty.call(tempFileData, originKey)) ||
      originKey === renameKey
    ) {
      return;
    }

    let finalKey = renameKey;

    try {
      if (isCreating) {
        if (beforeCreate) {
          const result = await beforeCreate(node, renameKey, Boolean(node.isFolder));

          if (result === false) {
            deleteFileOrFolder(originKey, !node.isFolder, true);
            return;
          }
          if (result && typeof result === 'string') {
            finalKey = result;
          }
        }
      } else {
        if (beforeRename) {
          const result = await beforeRename(node, originKey, renameKey, Boolean(node.isFolder));
          if (result === false) {
            return;
          }
          if (result && typeof result === 'string') {
            finalKey = result;
          }
        }
      }
    } catch (error) {
      if (isCreating) {
        // If beforeCreate throw error(Promise.reject), delete the file/folder
        deleteFileOrFolder(originKey, !node.isFolder, true);
      }
      return;
    }

    let tempFileDataCopy = { ...tempFileData };

    if (isFile) {
      tempFileDataCopy[finalKey] = tempFileDataCopy[originKey];
      delete tempFileDataCopy[originKey];
    } else {
      const regx = new RegExp(`^${transformRegexSpecChar(originKey)}`); // prefix originKey
      // change folder, in other word, change all file under this folder
      tempFileDataCopy = Object.keys(tempFileDataCopy).reduce((sum, current) => {
        if (!!current.match(regx)) {
          const newKey = current.replace(regx, finalKey);
          sum[newKey] = tempFileDataCopy[current];
        } else {
          sum[current] = tempFileDataCopy[current];
        }

        return sum;
      }, {} as FileData);
    }

    setFileData(tempFileDataCopy);

    if (isCreating) {
      onCreateFinish?.(finalKey, !isFile);
    } else {
      onRenameFinish?.(node, originKey, finalKey);
    }

    // Auto selected new file node
    if (isCreating && isFile) {
      const extList = finalKey.split('.');
      const nameList = finalKey.split('/');
      const fileExt = extList && extList.length > 0 ? extList[extList.length - 1] : 'default';

      // trigger mock select event
      onSelect(
        [finalKey],
        {
          selected: true,
          node: {
            props: {
              dataRef: {
                ...node,
                title: nameList[nameList.length - 1],
                label: nameList[nameList.length - 1],
                key: finalKey,
                code: '',
                isLeaf: true,
                fileExt: fileExt,
                isFolder: false,
              },
            },
          },
          selectedNodes: [
            {
              ...node,
              title: nameList[nameList.length - 1],
              label: nameList[nameList.length - 1],
              key: finalKey,
              code: '',
              isLeaf: true,
              fileExt: fileExt,
              isFolder: false,
            },
          ],
          e: null as any,
        },
        true,
      );
    }
  }
  async function deleteFileOrFolder(key: string, isFile = true, isForceDelete = false) {
    if (!isForceDelete && beforeDelete) {
      try {
        const result = await beforeDelete(key, !isFile);
        if (result === false) {
          return;
        }
      } catch (error) {
        // beforeDelete return Promise.reject, do nothing
        return;
      }
    }

    const toBeDeleteKeys = [];
    let tempFileDataCopy = { ...tempFileData };
    if (isFile) {
      if (!Object.prototype.hasOwnProperty.call(tempFileData, key)) {
        return;
      }
      // delete node by key
      delete tempFileDataCopy[key];
      toBeDeleteKeys.push(key);
    } else {
      const regx = new RegExp(`^${transformRegexSpecChar(key)}`); // prefix originKey
      // delete folder, delete all file under this folder
      tempFileDataCopy = Object.keys(tempFileDataCopy).reduce((sum, current) => {
        if (!!current.match(regx)) {
          // delete
          toBeDeleteKeys.push(current);
          return sum;
        }

        sum[current] = tempFileDataCopy[current];

        return sum;
      }, {} as FileData);
    }

    if (!isCreating && onDeleteFinish) {
      onDeleteFinish(toBeDeleteKeys, key);
    }

    // Cancel focus mode
    if (focusKey === key) {
      setFocusKey(null);
    }
    setFileData(tempFileDataCopy);
  }

  function resetState() {
    setFocusKey(null);
    setIsCreating(false);
    setValidateObj({
      validateStatus: undefined,
      help: '',
    });
    isDeleteButtonClick.current = false;
  }
  function isValidateName(name: string, node: FileDataNode) {
    // validate empty
    if (!name) {
      setValidateObj({
        validateStatus: 'error',
        help: i18n.t('valid_error.empty_node_name_invalid'),
      });
      return false;
    }
    if (name === node.title) {
      return true;
    }
    // validate same file path
    let tempkey = '';
    if (node.parentKey) {
      tempkey = `${node.parentKey}/${name}`;
    } else {
      tempkey = `${name}`;
    }
    if (
      Object.prototype.hasOwnProperty.call(tempFileData, tempkey) ||
      Object.keys(tempFileData).some((innerPath) => {
        // Case: tempFileData = { 'main/test.py': '1' }, tempkey = "main"
        // There is a folder named "main", so it is not validate name
        return innerPath.startsWith(`${tempkey}/`);
      })
    ) {
      setValidateObj({
        validateStatus: 'error',
        help: i18n.t('valid_error.same_node_name_invalid'),
      });
      return false;
    }

    if (validateObj.validateStatus !== 'success') {
      setValidateObj({
        validateStatus: 'success',
        help: '',
      });
    }

    return true;
  }

  function onSelect(
    selectedKeys: Key[],
    info: {
      selected: boolean;
      selectedNodes: FileDataNode[];
      node: any;
      e: Event;
    },
    isForceSelect = false, // 扩展参数，表示是否强制选择
  ) {
    // Disable select handler in focus mode
    if (!isForceSelect && Boolean(focusKey)) return;

    const node = info?.node?.props.dataRef ?? {};
    const { key, isFolder, code } = node;

    if (info.selected && !isFolder) {
      if (isAsyncMode && Object.prototype.hasOwnProperty.call(filePathToIsReadMap.current, key)) {
        if (getFile) {
          if (filePathToIsReadMap.current[key]) {
            onSelectFile?.(key, code!, node);
          } else {
            setIsLoading(true);
            getFile(String(key))
              .then((fileContent) => {
                filePathToIsReadMap.current[key] = true;
                setFileData({
                  ...tempFileData,
                  [key]: fileContent,
                });
                node.code = fileContent;
                onSelectFile?.(key, fileContent, node);
                setIsLoading(false);
              })
              .catch((error) => {
                Message.error(error.message);
                setIsLoading(false);
              });
          }
        } else {
          onSelectFile?.(key, code!, node);
        }
      } else {
        onSelectFile?.(key, code!, node);
      }
    }
    if (isFolder) {
      if (expandedKeys.includes(key)) {
        setExpandedKeys([...expandedKeys.filter((item) => item !== key)]);
      } else {
        setExpandedKeys([...expandedKeys, key]);
      }
    }
    setSelectedKeys(selectedKeys);
    onSelectFromProps?.(selectedKeys, info as any);
  }
  function onExpand(expandedKeys: Array<Key>) {
    setExpandedKeys(expandedKeys);
  }
  async function onInputBlur(event: React.FocusEvent<HTMLInputElement>, node: FileDataNode) {
    event.stopPropagation();
    const inputValue = event.target.value;

    if (!isValidateName(inputValue, node)) {
      inputRef.current?.focus();
      return;
    }

    const finalKey = String(node.key).replace(String(node.title), inputValue);

    await renameFileOrFolder(node, finalKey);

    resetState();
  }
  async function onInputKeyPress(event: any, node: FileDataNode) {
    if (event.key === 'Escape') {
      if (isCreating) {
        // remove temp node
        await deleteFileOrFolder(String(focusKey), !node.isFolder, true);
      }
      resetState();
      return;
    }
    if (event.key === 'Enter') {
      const inputValue = event.target.value;

      if (!isValidateName(inputValue, node)) return;

      const finalKey = String(node.key).replace(String(node.title), inputValue);
      await renameFileOrFolder(node, finalKey);
      resetState();
      return;
    }
  }
  function onCreateFile(node?: FileDataNode, isFile?: boolean) {
    let tempKey = '';
    const folderKey = node ? (node.isFolder ? node.key : node.parentKey) : '';
    if (folderKey) {
      // set folder expand key
      setExpandedKeys((prevState) => [...prevState, folderKey]);
      // insert new temp node on folder
      tempKey = `${folderKey}/${giveWeakRandomKey()}`;
    } else {
      // insert new temp node on root
      tempKey = `${giveWeakRandomKey()}`;
    }

    setIsCreating(true);
    setFocusKey(tempKey);
    setFileData({ ...tempFileData, [tempKey]: isFile ? '' : null }); // null will be treated as folder
  }
  function onEditFile(node: FileDataNode) {
    onClickRename?.(node);
    setFocusKey(node.key);
  }
  function onDeleteFile(node: FileDataNode, isForceDelete = false) {
    deleteFileOrFolder(String(node.key), !node.isFolder, isForceDelete);
  }

  function selectFirstFileNode(fileTreeList: FileDataNode[] = formattedTreeData) {
    if (isAlreadySelectFirstNode.current) return;

    const node = getFirstFileNode(fileTreeList);

    // If there is no file node, isAutoSelectFirstFile will be invalid
    if (isAsyncMode && isAlreadyFetchedFileTreeList.current && !node) {
      isAlreadySelectFirstNode.current = true;
      return;
    }

    if (node) {
      isAlreadySelectFirstNode.current = true;
      // Trigger mock select event
      onSelect(
        [node.key],
        {
          selected: true,
          node: {
            props: {
              dataRef: {
                ...node,
                title: node.title,
                label: node.title as string,
              },
            },
          },
          selectedNodes: [
            {
              ...node,
              title: node.title,
              label: node.title as string,
            },
          ],
          e: null as any,
        },
        true,
      );
    }
  }
};

export default forwardRef(FileExplorer);
