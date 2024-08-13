/* istanbul ignore file */

import React, { useState } from 'react';
import ReactDOM from 'react-dom';

import { Drawer, DrawerProps, Button } from '@arco-design/web-react';
import CodeEditor, { CodeEditorProps } from 'components/CodeEditor';

export type CodeEditorDrawerProps = {
  visible: boolean;
  value?: string;
  onChange?: (val: string) => void;
  isReadOnly?: boolean;
  language?: string;
  theme?: string;
  drawerWidth?: string | number;
  container?: HTMLElement;
  onClose?: (params?: any) => void;
  codeEditorProps?: CodeEditorProps;
} & Pick<DrawerProps, 'title' | 'afterClose'>;

export type ButtonProps = Omit<CodeEditorDrawerProps, 'visible'> & {
  text?: string;
  children?: React.ReactNode;
};
export type ShowProps = Omit<CodeEditorDrawerProps, 'visible'>;

function CodeEditorDrawer({
  title,
  value,
  visible,
  container,
  language = 'json',
  isReadOnly = true,
  theme = 'grey',
  drawerWidth = '50%',
  codeEditorProps,
  afterClose,
  onClose,
  onChange,
}: CodeEditorDrawerProps) {
  return (
    <Drawer
      width={drawerWidth}
      visible={visible}
      title={title}
      closable={true}
      onCancel={onClose}
      unmountOnExit={true}
      afterClose={afterClose}
      getPopupContainer={() => container || window.document.body}
    >
      <CodeEditor
        language={language as any}
        isReadOnly={isReadOnly}
        theme={theme}
        value={value ?? ''}
        onChange={onChange}
        {...codeEditorProps}
      />
    </Drawer>
  );
}

function _Button({ text = '查看', children, ...restProps }: ButtonProps) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <Button size="small" onClick={() => setVisible(true)} type="text">
        {text}
      </Button>
      <CodeEditorDrawer visible={visible} {...restProps} onClose={() => setVisible(false)} />
    </>
  );
}

function show(props: ShowProps) {
  const key = `__code_editor_drawer_${Date.now()}__`;
  const container = window.document.createElement('div');
  container.style.zIndex = '1000';
  window.document.body.appendChild(container);

  _hide(props);
  _show(props);

  function _renderComp(props: CodeEditorDrawerProps) {
    ReactDOM.render(
      React.createElement(CodeEditorDrawer, {
        ...props,
        key,
        container,
        onClose() {
          props.onClose?.();
          _hide(props);
        },
      }),
      container,
    );
  }

  function _hide(props: ShowProps) {
    _renderComp({
      ...props,
      visible: false,
      afterClose() {
        window.document.body.removeChild(container);
      },
    });
  }

  function _show(props: ShowProps) {
    _renderComp({
      ...props,
      visible: true,
    });
  }
}

CodeEditorDrawer.show = show;
CodeEditorDrawer.Button = _Button;

export default CodeEditorDrawer;
