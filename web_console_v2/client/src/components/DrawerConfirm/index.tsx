// 给 Drawer 组件添加类似于 Modal.confirm 一样的功能

import React, { FC, useState } from 'react';
import ReactDOM from 'react-dom';
import styled from 'styled-components';

import { Drawer, DrawerProps, Button, Space } from '@arco-design/web-react';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';

type TSetParams = (params: any) => void;

export type TProps = {
  visible: boolean;
  container?: HTMLElement;
  renderContent: (setOkParams: TSetParams, setCloseParams: TSetParams) => React.ReactNode;
  okText?: string;
  cancelText?: string;
  onOk?: (params: any) => Promise<any>;
  onClose?: (params?: any) => void;
} & Pick<DrawerProps, 'title' | 'afterClose'>;

const StyledContainer = styled.div`
  font-size: 12px;
  color: rgb(var(--gray-8));
`;
const StyledButtonSpace = styled(Space)`
  margin-top: 28px;
`;

const ConfirmDrawer: FC<TProps> = ({
  title,
  okText,
  cancelText,
  visible,
  container,
  renderContent,
  afterClose,
  onOk,
  onClose,
}) => {
  const [confirming, setConfirming] = useState<boolean>(false);
  const [okParams, setOkParams] = useState<any>({});
  const [closeParams, setCloseParams] = useState<any>({});

  return (
    <Drawer
      width={400}
      visible={visible}
      maskClosable={false}
      title={title}
      closable={true}
      onCancel={onClose}
      unmountOnExit={true}
      afterClose={afterClose}
      getPopupContainer={() => container || window.document.body}
    >
      <StyledContainer>{renderContent(setOkParams, setCloseParams)}</StyledContainer>
      <StyledButtonSpace>
        <Button loading={confirming} onClick={onConfirmWrap} type="primary">
          {okText}
        </Button>
        <ButtonWithPopconfirm
          buttonProps={{
            disabled: confirming,
          }}
          buttonText={cancelText}
          onConfirm={() => {
            onClose?.(closeParams);
          }}
        />
      </StyledButtonSpace>
    </Drawer>
  );

  async function onConfirmWrap() {
    if (typeof onOk === 'function') {
      setConfirming(true);
      await onOk(okParams);
      setConfirming(false);
    }
    onClose?.();
  }
};

type TConfirmProps = Omit<TProps, 'visible'>;
function confirm(props: TConfirmProps) {
  const key = `__scale_drawer_${Date.now()}__`;
  const container = window.document.createElement('div');
  container.style.zIndex = '1000';
  window.document.body.appendChild(container);

  hide(props); // 先渲染组件
  show(props); // 再显示

  function renderComp(props: TProps) {
    ReactDOM.render(
      React.createElement(ConfirmDrawer, {
        ...props,
        key,
        container,
        async onOk(params) {
          if (props.onOk) {
            await props.onOk(params);
            hide(props);
          }
        },
        onClose() {
          if (props.onClose) {
            props.onClose();
          }
          hide(props);
        },
      }),
      container,
    );
  }

  function hide(props: TConfirmProps) {
    renderComp({
      ...props,
      visible: false,
      afterClose() {
        window.document.body.removeChild(container);
      },
    });
  }

  function show(props: TConfirmProps) {
    renderComp({
      ...props,
      visible: true,
    });
  }
}

export default confirm;
