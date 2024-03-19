/* istanbul ignore file */

import React, { FC, useState } from 'react';

import { Checkbox, Popconfirm } from '@arco-design/web-react';

import { CheckboxProps } from '@arco-design/web-react/es/Checkbox';

type Props = {
  /** Popconfirm title */
  title?: string;
  /** Checkbox text */
  text?: string;
  /** Popconfirm cancel button title */
  cancelText?: string;
  /** Popconfirm ok button title */
  okText?: string;
  /** Checkbox disabled */
  disabled?: boolean;
  /** Checkbox value */
  value?: boolean;
  onChange?: (val: boolean) => void;
} & CheckboxProps;
const CheckboxWithPopconfirm: FC<Props> = ({
  value,
  onChange,
  title,
  text,
  disabled,
  cancelText = '取消',
  okText = '确认',
  ...props
}) => {
  const [isShowCheckboxPopconfirm, setIsShowCheckboxPopconfirm] = useState(false);

  return (
    <>
      <Popconfirm
        popupVisible={isShowCheckboxPopconfirm}
        title={title}
        cancelText={cancelText}
        okText={okText}
        onOk={onCheckboxPopconfirmConfirm}
        onCancel={onCheckboxPopconfirmCancel}
      >
        <Checkbox checked={value} onChange={onCheckboxClick} disabled={disabled} {...props}>
          {text}
        </Checkbox>
      </Popconfirm>
    </>
  );
  function onCheckboxClick(e: any) {
    if (disabled) {
      return;
    }

    if (value) {
      onChange && onChange(false);
    } else {
      setIsShowCheckboxPopconfirm(true);
    }
  }

  function onCheckboxPopconfirmConfirm() {
    setIsShowCheckboxPopconfirm(false);
    onChange && onChange(true);
  }
  function onCheckboxPopconfirmCancel() {
    setIsShowCheckboxPopconfirm(false);
    onChange && onChange(false);
  }
};

export default CheckboxWithPopconfirm;
