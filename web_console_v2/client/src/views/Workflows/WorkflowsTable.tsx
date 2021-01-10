import React, { useState } from 'react'
import styled from 'styled-components'
import { Row, Col, Button, Form, Input, Select, Table, message } from 'antd'
import { useList } from 'react-use'
import { Link } from 'react-router-dom'
import { useQuery } from 'react-query'
import { fetchWorkflowList } from 'services/workflow'
import i18n from 'i18n'
import { formatTimestamp } from 'shared/date'
import { useTranslation } from 'react-i18next'
import ListPageLayout from 'components/ListPageLayout'

const FilterItem = styled(Form.Item)`
  > .ant-form-item-control {
    width: 227px;
  }
`

const tableCols = [
  {
    title: i18n.t('workflow.name'),
    dataIndex: 'name',
    render: (text: string, record: any) => (
      <Link to={`/workflows/${record.id}`} rel="nopener">
        {text.toUpperCase()}
      </Link>
    ),
  },
  {
    title: i18n.t('workflow.col_status'),
    dataIndex: 'state',
    render: (state: string) => <div>{state}</div>,
  },
  {
    title: i18n.t('workflow.col_project'),
    dataIndex: 'project_id',
    render: (project: string) => <div>{project}</div>,
  },
  {
    title: i18n.t('workflow.col_creator'),
    dataIndex: 'creator',
    render: (creator: string) => <div>{creator}</div>,
  },
  {
    title: i18n.t('workflow.col_date'),
    dataIndex: 'created_at',
    render: (date: number) => <div>{formatTimestamp(date)}</div>,
  },
  {
    title: i18n.t('workflow.col_actions'),
    dataIndex: 'created_at',
    render: (_: any, record: any) => (
      <div>
        <Button type="link">{i18n.t('workflow.action_run')}</Button>
        {/* <Button type="link">{i18n.t('workflow.action_stop_running')}</Button> */}
        {/* <Button type="link">{i18n.t('workflow.action_re_run')}</Button> */}
        <Button type="link">{i18n.t('workflow.action_duplicate')}</Button>
        <Button type="link">{i18n.t('workflow.action_detail')}</Button>
      </div>
    ),
  },
]

type QueryParams = {
  project?: string
  name?: string
}

function WorkflowsTable() {
  const { t } = useTranslation()
  const [form] = Form.useForm<QueryParams>()
  const [projectList] = useList([{ value: '', label: i18n.t('all') }])
  const [params, setParams] = useState<QueryParams>({
    project: '',
    name: undefined,
  })

  const { isLoading, isError, data: res, error } = useQuery(
    ['fetchWorkflowList', params.project, params.name],
    () => fetchWorkflowList(params),
  )

  if (isError && error) {
    message.error((error as Error).message)
  }

  function handleSearch(values: QueryParams) {
    setParams(values)
  }

  return (
    <ListPageLayout title={t('term.workflow')}>
      <Row gutter={16} justify="space-between">
        <Col>
          <Link to="/workflows/create">
            <Button type="primary">{t('workflow.create_workflow')}</Button>
          </Link>
        </Col>
        <Col>
          <Form initialValues={{ project: '' }} layout="inline" form={form} onFinish={handleSearch}>
            <FilterItem name="project" label={t('term.project')}>
              <Select onChange={form.submit}>
                {projectList.map((item) => (
                  <Select.Option key={item.value} value={item.value}>
                    {item.label}
                  </Select.Option>
                ))}
              </Select>
            </FilterItem>
            <FilterItem name="name">
              <Input.Search
                placeholder={t('workflow.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </FilterItem>
          </Form>
        </Col>
      </Row>

      <Table loading={isLoading} dataSource={res?.data.data || []} columns={tableCols} />
    </ListPageLayout>
  )
}

export default WorkflowsTable
