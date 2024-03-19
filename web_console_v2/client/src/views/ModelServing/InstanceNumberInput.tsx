import React from 'react';
import { InputNumber, InputNumberProps, Space } from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';

import styles from './InstanceNumberInput.module.less';

const InstanceNumberInput: React.FC<InputNumberProps> = (props) => {
  return (
    <Space size="large">
      <InputNumber
        className={styles.input_number_container}
        mode="button"
        precision={0}
        {...props}
      />
      <span>
        <IconInfoCircle className={styles.info_icon_container} />
        实例数范围1～100
      </span>
    </Space>
  );
};

export default InstanceNumberInput;
