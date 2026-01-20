/* istanbul ignore file */

import React, { FC } from 'react';
import i18n from 'i18n';

import { Popconfirm, Button } from '@arco-design/web-react';
import { PopconfirmProps } from '@arco-design/web-react/es/Popconfirm';
import { ButtonProps } from '@arco-design/web-react/es/Button';

export interface Props {
  onCancel?: () => void;
  onConfirm?: () => void;
  /** Popconfirm title */
  title?: React.ReactNode;
  /** Button title */
  buttonText?: React.ReactNode;
  /** Popconfirm ok button title */
  okText?: string;
  /** Popconfirm cancel button title */
  cancelText?: string;
  /** Arco button props */
  buttonProps?: ButtonProps;
  /** Arco popconfirmutton props */
  popconfirmProps?: PopconfirmProps;
}

const ButtonWithPopconfirm: FC<Props> = ({
  title = i18n.t('msg_quit_warning'),
  buttonText = i18n.t('cancel'),
  okText = i18n.t('submit'),
  cancelText = i18n.t('cancel'),
  onCancel,
  onConfirm,
  buttonProps,
  popconfirmProps,
}) => {
  return (
    <Popconfirm
      title={title}
      cancelText={cancelText}
      okText={okText}
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...popconfirmProps}
    >
      <Button {...buttonProps}>{buttonText}</Button>
    </Popconfirm>
  );
};

export default ButtonWithPopconfirm;
