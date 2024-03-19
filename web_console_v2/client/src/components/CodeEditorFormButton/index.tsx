/* istanbul ignore file */

import React, { FC, useState } from 'react';
import styled from 'styled-components';

import { Button } from '@arco-design/web-react';
import { IconCodeSquare } from '@arco-design/web-react/icon';
import { FileData } from 'components/FileExplorer';
import CodeEditorModal, { Props as CodeEditorModalProps } from 'components/CodeEditorModal';

export type Props = {
  value?: FileData;
  onChange?: (val?: FileData) => any;
  disabled?: boolean;
  buttonText?: string;
  buttonType?: 'default' | 'primary' | 'secondary' | 'dashed' | 'text' | 'outline';
  buttonIcon?: React.ReactNode;
  buttonStyle?: React.CSSProperties;
} & Partial<CodeEditorModalProps>;

const Container = styled.div``;

const CodeEditorFormButton: FC<Props> = ({
  value,
  onChange,
  disabled,
  buttonStyle = {},
  buttonText = '打开代码编辑器',
  buttonType = 'default',
  buttonIcon = <IconCodeSquare />,
  title = '代码编辑器',
  ...resetProps
}) => {
  const [isShowCodeEditorModal, setIsShowCodeEditorModal] = useState(false);

  return (
    <Container>
      <Button
        icon={buttonIcon}
        onClick={onButtonClick}
        style={buttonStyle}
        disabled={disabled}
        type={buttonType}
      >
        {buttonText}
      </Button>
      <CodeEditorModal
        visible={isShowCodeEditorModal}
        initialFileData={value ?? {}}
        onClose={onCloseButtonClick}
        onSave={onSave}
        title={title}
        {...resetProps}
      />
    </Container>
  );

  function onButtonClick() {
    setIsShowCodeEditorModal(true);
  }
  function onCloseButtonClick() {
    setIsShowCodeEditorModal(false);
  }
  function onSave(fileData: FileData) {
    onChange && onChange(fileData);
  }
};

export default CodeEditorFormButton;
