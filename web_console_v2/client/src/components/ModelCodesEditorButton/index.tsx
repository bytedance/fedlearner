import { Button, Drawer, Row, Col } from 'antd';
import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { CodeOutlined } from '@ant-design/icons';
import { useToggle } from 'react-use';
import CodeEditor, { VS_DARK_COLOR } from 'components/CodeEditor';
import FileExplorer from './FileExplorer';
import { isEmpty } from 'lodash';

const DEFAULT_MAIN_FILE = 'main.py';

const Container = styled.div``;

const StyledDrawer = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding: 10px 0 0;
    height: 100%;
    background-color: ${VS_DARK_COLOR};
  }
`;
type MultiPathCodes = { [path: string]: string };
type Props = {
  value?: MultiPathCodes;
  onChange?: (val?: MultiPathCodes) => any;
};

let __onChangeTimer: number;

const CodeEditorButton: FC<Props> = ({ value, onChange }) => {
  let data: MultiPathCodes = value!;

  if (typeof data === 'string' || isEmpty(data)) {
    data = { [DEFAULT_MAIN_FILE]: '' };
  }

  const files = Object.keys(data || {});

  const [visible, toggleVisible] = useToggle(false);
  const [activeFile, setActive] = useState<string>(files[0]);

  return (
    <Container>
      <Button icon={<CodeOutlined />} onClick={onButtonClick}>
        打开模型代码编辑器
      </Button>

      <StyledDrawer
        getContainer="#app-content"
        placement="left"
        width={window.innerWidth - 250}
        visible={visible}
        contentWrapperStyle={{
          contain: 'paint',
        }}
        bodyStyle={{
          overflow: 'hidden',
        }}
        headerStyle={{
          display: 'none',
        }}
        maskStyle={{ backdropFilter: 'blur(3px)' }}
        onClose={toggleVisible}
      >
        <Row style={{ height: '100%' }} wrap={false}>
          <FileExplorer
            files={files}
            active={activeFile}
            onSelect={onFileSelect}
            onCreate={onFileCreate}
            onDelete={onFileDelete}
          />
          <Col flex="1">
            <CodeEditor
              path={activeFile}
              value={data[activeFile]}
              defaultValue={data[activeFile]}
              defaultPath={activeFile}
              language="python"
              onChange={onCodeChange}
            />
          </Col>
        </Row>
      </StyledDrawer>
    </Container>
  );

  function onButtonClick() {
    toggleVisible();
  }
  function onCodeChange(val?: string) {
    data[activeFile] = val || '';

    updateValue(data);
  }
  function onFileSelect(path: string) {
    setActive(path);
  }
  function onFileCreate(newPath: string) {
    data[newPath] = '# coding: utf-8\n';

    onChange && onChange(data);

    setActive(newPath);
  }
  function onFileDelete() {
    if (data[activeFile]) {
      delete data[activeFile];
    }
    onChange && onChange(data);
  }

  function updateValue(val: MultiPathCodes) {
    clearTimeout(__onChangeTimer);

    setTimeout(() => {
      onChange && onChange(val);
    }, 200);
  }
};

export default CodeEditorButton;
