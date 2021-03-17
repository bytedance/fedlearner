import { Button, Drawer } from 'antd';
import React, { FC } from 'react';
import styled from 'styled-components';
import { CodeOutlined } from '@ant-design/icons';
import { useToggle } from 'react-use';
import CodeEditor from 'components/CodeEditor';

const Container = styled.div``;

const StyledDrawer = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding: 10px 0 0;
    height: 100%;
    background-color: #1e1e1e;
  }
`;

type Props = {
  value?: string;
  onChange?: (val: string) => any;
};

const CodeEditorButton: FC<Props> = ({ value, onChange }) => {
  const [visible, toggleVisible] = useToggle(false);

  return (
    <Container>
      <Button icon={<CodeOutlined />} onClick={onButtonClick}>
        打开编辑器
      </Button>

      <StyledDrawer
        getContainer="#app-content"
        placement="left"
        width={window.innerWidth - 400}
        visible={visible}
        contentWrapperStyle={{
          boxShadow: 'none',
        }}
        headerStyle={{
          display: 'none',
        }}
        maskStyle={{ backdropFilter: 'blur(3px)' }}
        onClose={toggleVisible}
      >
        <CodeEditor value={value} language="json" onChange={onCodeChange} />
      </StyledDrawer>
    </Container>
  );

  function onButtonClick() {
    toggleVisible();
  }
  function onCodeChange(val?: string) {
    onChange && onChange(val || '');
  }
};

export default CodeEditorButton;
