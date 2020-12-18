import React, { useState } from 'react'
import styled from 'styled-components'
import { MixinCircle } from 'styles/mixins'
import { Modal, Switch, Table, Tag, Input, Divider, Tooltip } from 'antd'
import { useToggle } from 'react-use'
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys'
import { toggleRequestMockState } from './utils'
import { useListenKeyboard, useReactiveLocalStorage } from 'hooks'
import store from 'store2'
import { ApiTwoTone } from '@ant-design/icons'

const FloatButton = styled.button`
  ${MixinCircle(43)}

  position: fixed;
  right: 8px;
  bottom: 64px;
  background-color: white;
  color: white;
  cursor: pointer;
  font-size: 12px;
  border: 2px solid #333;

  &,
  &:focus,
  &:active {
    border: none;
    outline: none;
    box-shadow: none;
  }
`

const Kbd = styled.kbd`
  padding: 0 5px;
  font-size: 12px;
  background-color: #fff;
  color: var(--darkGray1);
  border-radius: 2px;
}
`

const methodColor: { [key: string]: string } = {
  get: 'blue',
  post: 'green',
  put: 'orange',
  patch: 'cyan',
  delete: 'red',
}

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
    title: 'Toggle',
    key: 'key',
    render: (_: any, record: { key: string; value: boolean }) => (
      <Switch checked={record.value} onChange={(val) => toggleRequestMockState(record.key, val)} />
    ),
  },
]

const MOCK_BUTTON_VISIBLE_KEY = 'mock_button_visible'

function MockDevtools() {
  const [keyword, setKeyword] = useState('')
  const [visible] = useReactiveLocalStorage<any>(MOCK_BUTTON_VISIBLE_KEY, false)
  const [modalVisible, toggleModal] = useToggle(false)
  const [mockConfigs] = useReactiveLocalStorage<{ [key: string]: boolean }>(
    LOCAL_STORAGE_KEYS.mock_configs,
  )

  useListenKeyboard('ctrl + m', () => {
    const curr = store.get(MOCK_BUTTON_VISIBLE_KEY)
    store.set(MOCK_BUTTON_VISIBLE_KEY, !curr)
  })

  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  const dataSource = Object.entries(mockConfigs || {})
    .map(([key, value]) => {
      const [method, path] = key.split('|')
      return {
        key,
        method,
        path,
        value,
      }
    })
    .filter(({ path }) => path.includes(keyword))

  return (
    <>
      {visible.toString() === 'true' && (
        <Tooltip
          placement="left"
          title={() => (
            <>
              Mock 控制面板，<Kbd>Ctrl</Kbd> + <Kbd>M</Kbd> 切换按钮的 隐藏/显示
            </>
          )}
        >
          <FloatButton onClick={toggleModal}>
            <ApiTwoTone style={{ fontSize: '18px' }} />
          </FloatButton>
        </Tooltip>
      )}

      <Modal
        title="Mock 接口列表"
        centered
        visible={modalVisible}
        onOk={() => toggleModal(false)}
        onCancel={() => toggleModal(false)}
        width={1000}
      >
        <Input.Search placeholder="根据 Path 搜索" onSearch={setKeyword} enterButton />
        <Divider />

        <Table
          columns={tableCols}
          size="small"
          dataSource={dataSource}
          pagination={{ pageSize: 10 }}
        />
      </Modal>
    </>
  )
}

export default MockDevtools
