/* istanbul ignore file */

import React, { useState } from 'react';
import styled from 'styled-components';
import { MixinCircle } from 'styles/mixins';
import { Modal, Switch, Table, Tag, Input, Divider, Tooltip, Button } from '@arco-design/web-react';
import { useToggle } from 'react-use';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { removeRequestMock, toggleRequestMockState } from './utils';
import { useListenKeyboard, useReactiveLocalStorage } from 'hooks';
import store from 'store2';
import { Storage } from 'components/IconPark';

const FloatButton = styled.button`
  ${MixinCircle(50)}

  position: fixed;
  z-index: 9999;
  right: 5px;
  bottom: 64px;
  background-color: rgb(var(--blue-1));
  color: white;
  cursor: pointer;
  font-size: 12px;

  &,
  &:focus,
  &:active {
    border: none;
    outline: none;
    box-shadow: none;
  }
`;
const Kbd = styled.kbd`
  padding: 0 5px;
  font-size: 12px;
  background-color: #fff;
  color: rgb(var(--gray-10));
  border-radius: 2px;
`;

const methodColor: { [key: string]: string } = {
  get: 'blue',
  post: 'green',
  put: 'orange',
  patch: 'cyan',
  delete: 'red',
};

const tableCols = [
  {
    title: 'Method',
    dataIndex: 'method',
    render: (text: string) => (
      <Tag color={methodColor[text.toLowerCase()]}>{text.toUpperCase()}</Tag>
    ),
  },
  {
    title: 'Path',
    dataIndex: 'path',
    render: (text: string) => <h4>{text}</h4>,
  },
  {
    title: 'Enable mock',
    key: 'toggle',
    render: (_: any, record: { key: string; value: boolean }) => (
      <Switch checked={record.value} onChange={(val) => toggleRequestMockState(record.key, val)} />
    ),
  },
  {
    title: 'Actions',
    key: 'actions',
    render: (_: any, record: { key: string }) => (
      <Button type="text" status="danger" onClick={() => removeRequestMock(record.key)}>
        删除
      </Button>
    ),
  },
];

const MOCK_BUTTON_VISIBLE_KEY = 'mock_button_visible';

/* i18n ignore */
function MockControlPanel() {
  const [keyword, setKeyword] = useState('');
  const [visible] = useReactiveLocalStorage<any>(MOCK_BUTTON_VISIBLE_KEY, false);
  const [modalVisible, toggleModal] = useToggle(false);
  const [mockConfigs] = useReactiveLocalStorage<{ [key: string]: boolean }>(
    LOCAL_STORAGE_KEYS.mock_configs,
  );

  useListenKeyboard('ctrl + m', () => {
    const curr = store.get(MOCK_BUTTON_VISIBLE_KEY);
    store.set(MOCK_BUTTON_VISIBLE_KEY, !curr);
  });

  if (process.env.NODE_ENV === 'development' || process.env.REACT_APP_ENABLE_FULLY_MOCK) {
    const dataSource = Object.entries(mockConfigs || {})
      .map(([key, value]) => {
        const [method, path] = key.split('|');
        return {
          key,
          method,
          path,
          value,
        };
      })
      .filter(({ path }) => path.includes(keyword));

    return (
      <>
        {visible.toString() === 'true' && (
          <Tooltip
            position="left"
            content={() => (
              <>
                Mock 控制面板，<Kbd>Ctrl</Kbd> + <Kbd>M</Kbd> 切换按钮的 隐藏/显示
              </>
            )}
          >
            <FloatButton onClick={toggleModal}>
              <Storage style={{ fontSize: '24px', color: 'var(--primaryColor)' }} />
            </FloatButton>
          </Tooltip>
        )}

        <Modal
          title="Mock 接口列表"
          alignCenter
          visible={modalVisible}
          onOk={() => toggleModal(false)}
          onCancel={() => toggleModal(false)}
          style={{ width: '1000px' }}
        >
          <Input.Search placeholder="根据 Path 搜索" onSearch={setKeyword} searchButton />
          <Divider />

          <Table columns={tableCols} size="small" data={dataSource} pagination={{ pageSize: 10 }} />
        </Modal>
      </>
    );
  }

  return null;
}

export default MockControlPanel;
