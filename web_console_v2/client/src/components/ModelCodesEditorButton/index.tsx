/* istanbul ignore file */

import { Button, Drawer, Grid } from '@arco-design/web-react';
import React, { FC, useState, useMemo } from 'react';
import { IconCodeSquare } from '@arco-design/web-react/icon';
import { useToggle } from 'react-use';
import CodeEditor from 'components/CodeEditor';

import FileExplorer from './FileExplorer';
import { isEmpty } from 'lodash-es';

import { BaseButtonProps } from '@arco-design/web-react/es/Button/interface';

import styles from './index.module.less';

const { Row, Col } = Grid;

const DEFAULT_MAIN_FILE = 'main.py';

type MultiPathCodes = { [path: string]: string };
type Props = {
  value?: MultiPathCodes;
  onChange?: (val?: MultiPathCodes) => any;
  disabled?: boolean;
  buttonText?: string;
  buttonType?: BaseButtonProps['type'];
  buttonIcon?: React.ReactNode;
  buttonStyle?: React.CSSProperties;
  renderButton?: (onClick: any) => React.ReactNode;
};

let __onChangeTimer: number;

const CodeEditorButton: FC<Props> = ({
  value,
  onChange,
  disabled,
  buttonText = '打开代码编辑器',
  buttonType = 'default',
  buttonIcon = <IconCodeSquare />,
  buttonStyle = {},
  renderButton,
}) => {
  const data = useMemo<MultiPathCodes>(() => {
    let tempData;
    if (typeof value === 'string' || isEmpty(value)) {
      tempData = { [DEFAULT_MAIN_FILE]: '' };
    } else {
      tempData = { ...value };
    }

    return tempData;
  }, [value]);

  const files = Object.keys(data || {});
  const [visible, toggleVisible] = useToggle(false);
  const [activeFile, setActive] = useState<string>(files[0]);

  return (
    <div>
      {renderButton ? (
        renderButton(onButtonClick)
      ) : (
        <Button icon={buttonIcon} onClick={onButtonClick} style={buttonStyle} type={buttonType}>
          {buttonText}
        </Button>
      )}

      <Drawer
        className={styles.drawer_container}
        placement="left"
        width={window.innerWidth - 250}
        visible={visible}
        style={{
          contain: 'paint',
        }}
        bodyStyle={{
          overflow: 'hidden',
        }}
        headerStyle={{
          display: 'none',
        }}
        footer={null}
        maskStyle={{ backdropFilter: 'blur(3px)' }}
        onCancel={toggleVisible}
      >
        <Row style={{ height: '100%', flexWrap: 'nowrap' }}>
          <FileExplorer
            files={files}
            active={activeFile}
            onSelect={onFileSelect}
            onCreate={onFileCreate}
            onDelete={onFileDelete}
            isReadOnly={disabled}
          />
          <Col flex="1" style={{ height: '100%' }}>
            <CodeEditor
              path={activeFile}
              value={data[activeFile]}
              defaultValue={data[activeFile]}
              defaultPath={activeFile}
              language="python"
              onChange={onCodeChange}
              isReadOnly={disabled}
            />
          </Col>
        </Row>
      </Drawer>
    </div>
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
  function onFileDelete(path: string) {
    if (Object.prototype.hasOwnProperty.call(data, path)) {
      delete data[path];
    }
    if (path === activeFile) {
      const tempFiles = files.filter((fileKey) => fileKey !== path);

      // replace active file
      setActive(tempFiles.length > 0 ? tempFiles[0] : '');
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
