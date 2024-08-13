/* istanbul ignore file */

import React, { FC } from 'react';
import i18n from 'i18n';

import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';

import { Modal } from '@arco-design/web-react';

import { ModalProps } from '@arco-design/web-react/es/Modal/modal';
import { ConfirmProps } from '@arco-design/web-react/es/Modal/confirm';

type ModalType = typeof Modal & {
  delete: (props: ConfirmProps) => ReturnType<typeof Modal.confirm>;
  stop: (props: ConfirmProps) => ReturnType<typeof Modal.confirm>;
  terminate: (props: ConfirmProps) => ReturnType<typeof Modal.confirm>;
  reject: (props: ConfirmProps) => ReturnType<typeof Modal.confirm>;
};

export const CUSTOM_CLASS_NAME = 'custom-modal';

export function withConfirmProps(props: ConfirmProps) {
  return {
    className: CUSTOM_CLASS_NAME,
    zindex: Z_INDEX_GREATER_THAN_HEADER,
    okText: i18n.t('confirm'),
    cancelText: i18n.t('cancel'),
    ...props,
  };
}

export function withDeleteProps(props: ConfirmProps) {
  return withConfirmProps({
    okText: i18n.t('delete'),
    okButtonProps: {
      status: 'danger',
    },
    ...props,
  });
}

export function withStopProps(props: ConfirmProps) {
  return withConfirmProps({
    okText: i18n.t('stop'),
    okButtonProps: {
      status: 'danger',
    },
    ...props,
  });
}

export function withTerminate(props: ConfirmProps) {
  return withConfirmProps({
    okText: i18n.t('terminate'),
    okButtonProps: {
      status: 'danger',
    },
    ...props,
  });
}

export function withRejectProps(props: ConfirmProps) {
  return withConfirmProps({
    okText: '确认拒绝',
    okButtonProps: {
      status: 'danger',
    },
    ...props,
  });
}

const ProxyModal: FC<ModalProps> = (props) => {
  return <Modal wrapClassName={CUSTOM_CLASS_NAME} {...props} />;
};

const MyModal = ProxyModal as ModalType;

// Custom method
MyModal.delete = (props: ConfirmProps) => {
  return Modal.confirm(withDeleteProps(props));
};
MyModal.stop = (props: ConfirmProps) => {
  return Modal.confirm(withStopProps(props));
};
MyModal.terminate = (props: ConfirmProps) => {
  return Modal.confirm(withTerminate(props));
};
MyModal.reject = (props: ConfirmProps) => {
  return Modal.confirm(withRejectProps(props));
};

// Proxy all static method
MyModal.info = (props: ConfirmProps) => Modal.info(withConfirmProps(props));
MyModal.success = (props: ConfirmProps) => Modal.success(withConfirmProps(props));
MyModal.error = (props: ConfirmProps) => Modal.error(withConfirmProps(props));
MyModal.warning = (props: ConfirmProps) => Modal.warning(withConfirmProps(props));
MyModal.confirm = (props: ConfirmProps) => Modal.confirm(withConfirmProps(props));
MyModal.destroyAll = () => Modal.destroyAll();
MyModal.useModal = () => Modal.useModal();

export default MyModal;
