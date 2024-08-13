/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';

import GridRow from 'components/_base/GridRow';
import { Left } from 'components/IconPark';
import Modal, { CUSTOM_CLASS_NAME } from 'components/Modal';

const Container = styled.div`
  cursor: pointer;
`;

type Props = {
  /** the className prop of confirm modal */
  modalClassName?: string;
  /** Alias onOK of Modal's props when isShowConfirmModal = true */
  onClick?: (evt: React.MouseEvent) => void;
  /** Show confirm modal after click children */
  isShowConfirmModal?: boolean;
  /** Modal title when isShowConfirmModal = true */
  title?: string;
  /** Modal content when isShowConfirmModal = true */
  content?: string;
};
const BackButton: FC<Props> = ({
  onClick,
  isShowConfirmModal = false,
  title = '确认要退出？',
  content = '退出后，当前所填写的信息将被清空。',
  children,
  modalClassName = CUSTOM_CLASS_NAME,
}) => {
  return (
    <Container onClick={onEleClick}>
      <GridRow gap="7.5" align="center">
        <Left style={{ fontSize: 8 }} />
        {children}
      </GridRow>
    </Container>
  );

  function onEleClick(evt: React.MouseEvent) {
    if (isShowConfirmModal) {
      Modal.confirm({
        className: modalClassName,
        title: title,
        content: content,
        onOk() {
          onClick?.(evt);
        },
      });
    } else {
      onClick?.(evt);
    }
  }
};

export default BackButton;
