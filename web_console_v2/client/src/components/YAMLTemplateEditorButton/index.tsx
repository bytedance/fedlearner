/* istanbul ignore file */

import { Button, Drawer } from '@arco-design/web-react';
import React, { FC } from 'react';
import { useToggle } from 'react-use';
import CodeEditor from 'components/CodeEditor';
import { formatJSONValue } from 'shared/helpers';

import styles from './index.module.less';
import { IconCodeSquare } from '@arco-design/web-react/icon';

type Props = {
  value?: string;
  onChange?: (val: string) => any;
  disabled?: boolean;
  language?: string;
  isCheck?: boolean;
};

const CodeEditorButton: FC<Props> = ({
  value,
  onChange,
  disabled,
  language = 'python',
  isCheck,
}) => {
  const [visible, toggleVisible] = useToggle(false);

  return (
    <div>
      <Button icon={<IconCodeSquare />} onClick={onButtonClick}>
        打开编辑器
      </Button>

      <Drawer
        className={styles.drawer_container}
        placement="left"
        width={window.innerWidth - 400}
        visible={visible}
        headerStyle={{
          display: 'none',
        }}
        bodyStyle={{ overflow: 'hidden' }}
        maskStyle={{ backdropFilter: 'blur(3px)' }}
        onCancel={toggleVisible}
        footer={null}
      >
        <CodeEditor
          value={language === 'json' ? formatJSONValue(value || '') : value}
          language={language as any}
          onChange={onCodeChange}
          isReadOnly={disabled || isCheck}
        />
      </Drawer>
    </div>
  );

  function onButtonClick() {
    toggleVisible();
  }
  function onCodeChange(val?: string) {
    onChange && onChange(val || '');
  }
};

export default CodeEditorButton;
