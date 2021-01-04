import React from 'react'
import styled from 'styled-components'
import { Row, Col, Button, Form, Input, Select, Table, message, Card } from 'antd'
import { useList } from 'react-use'
import { Link, useHistory } from 'react-router-dom'
import { useQuery } from 'react-query'
import { fetchWorkflowList } from 'services/workflow'
import i18n from 'i18n'
import { formatTimestamp } from 'shared/date'
import { useTranslation } from 'react-i18next'

const FilterItem = styled(Form.Item)`
  > .ant-form-item-control {
    width: 227px;
  }
`

const DataTable = styled(Table)`
  margin-top: 18px;
`

const tableCols = [
  {
    title: i18n.t('workflows.name'),
    dataIndex: 'name',
    render: (text: string, record: any) => (
      <Link to={`/workflows/${record.id}`} rel="nopener">
        {text.toUpperCase()}
      </Link>
    ),
  },
  {
    title: i18n.t('workflows.col_status'),
    dataIndex: 'status',
    render: (status: string) => <div>{status}</div>,
  },
  {
    title: i18n.t('workflows.col_project'),
    dataIndex: 'project_token',
    render: (project: string) => <div>{project}</div>,
  },
  {
    title: i18n.t('workflows.col_creator'),
    dataIndex: 'creator',
    render: (creator: string) => <div>{creator}</div>,
  },
  {
    title: i18n.t('workflows.col_date'),
    dataIndex: 'create_at',
    render: (date: number) => <div>{formatTimestamp(date)}</div>,
  },
  {
    title: i18n.t('workflows.col_actions'),
    dataIndex: 'create_at',
    render: (_: any, record: any) => (
      <div>
        <Button type="link">{i18n.t('workflows.action_run')}</Button>
        {/* <Button type="link">{i18n.t('workflows.action_stop_running')}</Button> */}
        {/* <Button type="link">{i18n.t('workflows.action_re_run')}</Button> */}
        <Button type="link">{i18n.t('workflows.action_duplicate')}</Button>
        <Button type="link">{i18n.t('workflows.action_detail')}</Button>
      </div>
    ),
  },
]

function WorkflowsTable() {
  const [form] = Form.useForm()
  const history = useHistory()
  const { t } = useTranslation()
  const [projectList] = useList([{ value: 'all', label: '全部' }])

  const { isLoading, isError, data: res, error } = useQuery('fetchWorkflowList', fetchWorkflowList)

  if (isError && error) {
    message.error((error as Error).message)
  }

  function handleSearch(query: any) {
    history.push('/workflows/create/basic')
  }

  return (
    <Card>
      <Row gutter={16} justify="space-between">
        <Col>
          <Link to="/workflows/create">
            <Button type="primary">创建工作流</Button>
          </Link>
        </Col>
        <Col>
          <Form
            initialValues={{ project: 'all' }}
            layout="inline"
            form={form}
            onFinish={handleSearch}
          >
            <FilterItem name="project" label="项目">
              <Select onChange={form.submit}>
                {projectList.map((item) => (
                  <Select.Option key={item.value} value={item.value}>
                    {item.label}
                  </Select.Option>
                ))}
              </Select>
            </FilterItem>
            <FilterItem name="keyword">
              <Input.Search
                placeholder={t('workflows.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </FilterItem>
          </Form>
        </Col>
      </Row>

      <DataTable loading={isLoading} dataSource={res?.data?.list || []} columns={tableCols} />
    </Card>
  )
}

export default WorkflowsTable
