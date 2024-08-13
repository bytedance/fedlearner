import React, { FC } from 'react';
import styled from 'styled-components';
import pythonSvg from 'assets/icons/python.svg';
import { VS_DARK_COLOR } from 'components/CodeEditor';
import { Tooltip, Grid, Input, Message } from '@arco-design/web-react';
import { PlusCircle, MinusCircle, Undo } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import { useToggle } from 'react-use';

const Row = Grid.Row;

const Container = styled.aside`
  position: sticky;
  top: 0;
  width: 240px;
  height: 100%;
  margin-top: -10px;
  padding: 10px 10px;
  background-color: #161616;
  color: var(--textColorSecondary);
`;

const FileList = styled.ul`
  list-style: none;
`;
const File = styled.li`
  margin-bottom: 5px;
  padding-right: 10px;
  font-size: 14px;
  cursor: pointer;
  line-height: 35px;
  text-indent: 30px;
  border-radius: 2px;
  background: url(${pythonSvg}) no-repeat 8px center / 14px;

  .del-button {
    opacity: 0;
    pointer-events: none;

    &:hover {
      color: var(--errorColor);
    }
  }

  &:hover {
    background-color: ${VS_DARK_COLOR};

    .del-button {
      pointer-events: all;
      opacity: 1;
    }
  }

  &.is-active {
    color: var(--textColorInverse);
    font-weight: bold;
  }
`;
const AddFileButton = styled(GridRow)`
  width: fit-content;
  padding: 7px 20px 7px 15px;
  margin-right: auto;
  color: var(--textColorSecondary);
  cursor: pointer;
  border-radius: 2px;

  &:hover {
    background-color: ${VS_DARK_COLOR};
  }
`;
const NewFileInput = styled(Input)`
  --bg: hsla(0, 0%, 100%, 0.12);
  margin-top: 20px;
  margin-bottom: -10px;
  background-color: var(--bg);
  color: white;

  &:focus {
    background-color: transparent;
  }
  &:hover {
    background-color: var(--bg);
  }
`;

type Props = {
  active: string;
  files: string[];
  isReadOnly?: boolean;
  onSelect?: (path: string) => void;
  onCreate?: (newPath: string) => void;
  onDelete?: (path: string) => void;
};

const FileExplorer: FC<Props> = ({
  files,
  active,
  onSelect,
  onCreate,
  onDelete,
  isReadOnly = false,
}) => {
  const [inputVisible, toggleInputVisible] = useToggle(false);

  return (
    <Container>
      <FileList>
        {files.map((file) => {
          return (
            <File
              key={file}
              className={active === file ? 'is-active' : ''}
              onClick={() => onFileClick(file)}
            >
              <Row justify="space-between" align="center">
                <span>{file}</span>
                {!isReadOnly && (
                  <Tooltip content="删除该文件" position="right" color="orange">
                    <MinusCircle
                      className="del-button"
                      onClick={(event) => onDelClick(file, event)}
                    />
                  </Tooltip>
                )}
              </Row>
            </File>
          );
        })}
      </FileList>

      {inputVisible && (
        <NewFileInput
          autoFocus
          placeholder="输入新建文件名，回车确认"
          onPressEnter={onConfirmAdd}
        />
      )}

      {!isReadOnly && (
        <AddFileButton gap="8" top="30" left="auto" onClick={onAddClick}>
          {inputVisible ? <Undo /> : <PlusCircle />}
          {inputVisible ? '取消添加' : '添加文件'}
        </AddFileButton>
      )}
    </Container>
  );

  function onDelClick(file: string, event: React.MouseEvent) {
    event.stopPropagation();
    onDelete && onDelete(file);
  }

  function onFileClick(file: string) {
    onSelect && onSelect(file);
  }
  function onAddClick() {
    toggleInputVisible();
  }
  function onConfirmAdd(event: React.KeyboardEvent<HTMLInputElement>) {
    const fileName = (event.target as any).value;

    if (!fileName) {
      Message.error('请输入文件名！');
      return;
    }

    onCreate && onCreate(fileName);
    toggleInputVisible();
  }
};

export default FileExplorer;
