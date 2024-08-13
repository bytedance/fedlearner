/* istanbul ignore file */

import React, { FC } from 'react';
import i18n from 'i18n';

import { Button } from '@arco-design/web-react';
import Modal from 'components/Modal';

import { ButtonProps } from '@arco-design/web-react/es/Button';

export interface Props extends ButtonProps {
  /** Alias onOK of Modal's props when isShowConfirmModal = true */
  onClick?: () => void;
  /** Show confirm modal after click children */
  isShowConfirmModal?: boolean;
  /** Modal title when isShowConfirmModal = true */
  title?: string;
  /** Modal content when isShowConfirmModal = true */
  content?: string;
}

const ButtonWithModalConfirm: FC<Props> = ({
  isShowConfirmModal = false,
  title = i18n.t('msg_quit_modal_title'),
  content = i18n.t('msg_quit_modal_content'),
  children,
  onClick,
  ...resetProps
}) => {
  return (
    <Button {...resetProps} onClick={_onClick}>
      {children}
    </Button>
  );

  function _onClick() {
    if (isShowConfirmModal) {
      Modal.confirm({
        title: title,
        content: content,
        onOk() {
          onClick?.();
        },
      });
    } else {
      onClick?.();
    }
  }
};

export default ButtonWithModalConfirm;
