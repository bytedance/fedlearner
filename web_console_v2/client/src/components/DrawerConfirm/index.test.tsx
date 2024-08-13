import React from 'react';
import { act, screen, fireEvent, waitFor } from '@testing-library/react';
import confirm from './index';

describe('<DrawerConfirm />', () => {
  it('should render in specific container', () => {
    const container = document.createElement('div');

    act(() => {
      confirm({
        container,
        renderContent: () => <div>content</div>,
      });
    });

    const drawer = document.querySelector('.arco-drawer');
    expect(drawer).toBeInTheDocument();
  });

  it('should called onOk and onClose', () => {
    let onOk = jest.fn(() => Promise.resolve(''));
    let onClose = jest.fn();
    const okText = 'okText' + Date.now();
    const cancelText = 'cancelText' + Date.now();

    act(() => {
      confirm({
        onOk,
        onClose,
        okText,
        cancelText,
        renderContent: () => <div>content</div>,
      });
    });

    const okBtn = screen.getByText(okText);

    fireEvent.click(okBtn);
    expect(onOk).toBeCalledTimes(1);
    expect(onClose).toBeCalledTimes(0);

    onOk = jest.fn(() => Promise.resolve(''));
    onClose = jest.fn();
    act(() => {
      confirm({
        onOk,
        onClose,
        okText,
        cancelText,
        renderContent: () => <div>content</div>,
      });
    });

    // 当前页面有两个 drawer
    const [, cancelBtn] = screen.getAllByText(cancelText);

    fireEvent.click(cancelBtn);

    // Click <ButtonWithPopconfirm/>'s submit button to close drawer
    fireEvent.click(screen.getAllByText('submit')[0]);

    expect(onOk).toBeCalledTimes(0);
    expect(onClose).toBeCalledTimes(1);
  });

  it('should remove container after close', () => {
    const container = document.createElement('div');
    const cancelText = 'cancelText' + Date.now();

    act(() => {
      confirm({
        container,
        cancelText,
        renderContent: () => <div>content</div>,
      });
    });

    const cancelBtn = screen.getByText(cancelText);
    fireEvent.click(cancelBtn);
    waitFor(() => {
      expect(container.querySelector('.arco-drawer')).toBeNull();
    });
  });
});
