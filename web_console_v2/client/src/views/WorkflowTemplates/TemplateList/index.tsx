import React, { FC, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { Link, useHistory } from 'react-router-dom';
import { deleteTemplate, fetchTemplateById, fetchWorkflowTemplateList } from 'services/workflow';
import styled from 'styled-components';
import ListPageLayout from 'components/ListPageLayout';
import NoResult from 'components/NoResult';
import { Col, Input, Row, Table, Form, Button, Tag, Popconfirm, message } from 'antd';
import { WorkflowTemplate } from 'typings/workflow';
import GridRow from 'components/_base/GridRow';
import { Experiment } from 'components/IconPark';
import { to } from 'shared/helpers';
import { useToggle } from 'react-use';

const ListContainer = styled.div`
  display: flex;
  flex: 1;
  width: 100%;
`;
const TemplateName = styled(Link)`
  font-size: 16px;
`;

const DownloadTemplate: FC<{ template: WorkflowTemplate }> = ({ template: { id, name } }) => {
  const { t } = useTranslation();

  const [loading, setLoading] = useToggle(false);

  return (
    <Button type="link" loading={loading} onClick={onClick}>
      {t('workflow.action_download')}
    </Button>
  );

  async function onClick() {
    setLoading(true);
    const [res, err] = await to(fetchTemplateById(id));
    setLoading(false);

    if (err) {
      return message.error(t('workflow.msg_get_tpl_detail_failed'));
    }

    const anchor = document.createElement('a');

    anchor.download = res.data.name + '.json';
    anchor.href = `data:text/json;charset=utf-8,${JSON.stringify(res.data)}`;

    anchor.click();
  }
};

const TemplateList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [form] = Form.useForm();
  const [params, setParams] = useState({ keyword: '' });

  const listQ = useQuery('fetchTemplateList', () => fetchWorkflowTemplateList(), {
    refetchOnWindowFocus: false,
  });

  const listData = listQ.data?.data;
  const isEmpty = listData?.length === 0;

  const columns = useMemo(
    () => [
      {
        title: t('workflow.col_tpl_name'),
        dataIndex: 'name',
        name: 'name',
        render: (name: string, record: WorkflowTemplate) => (
          <TemplateName to={`/workflow-templates/edit/basic/${record.id}`}>{name}</TemplateName>
        ),
      },
      {
        title: t('workflow.col_group_alias'),
        dataIndex: 'group_alias',
        name: 'group_alias',
      },
      {
        title: t('workflow.label_is_left'),
        dataIndex: 'is_left',
        name: 'is_left',
        render: (isLeft: string) => (
          <Tag color={isLeft ? 'green' : 'warning'}>{String(isLeft)}</Tag>
        ),
      },
      {
        title: t('workflow.col_actions'),
        dataIndex: 'operation',
        name: 'operation',
        render: (_: any, record: WorkflowTemplate) => {
          return (
            <GridRow gap="8">
              <DownloadTemplate template={record} />

              <Link to={`/workflow-templates/edit/basic/${record.id}`}>{t('edit')}</Link>

              <Popconfirm
                title={t('workflow.msg_sure_to_delete')}
                onConfirm={() => onDeleteConfirm(record)}
              >
                <Button size="small" type="link" danger>
                  {t('delete')}
                </Button>
              </Popconfirm>
            </GridRow>
          );
        },
      },
    ],
    [t],
  );

  return (
    <ListPageLayout
      title={
        <GridRow gap="4">
          <Experiment />
          {t('menu.label_workflow_tpl')}
        </GridRow>
      }
      tip="This feature is experimental"
    >
      <Row gutter={16} justify="space-between" align="middle">
        <Col>
          <Button size="large" type="primary" onClick={goCreate}>
            {t('workflow.create_tpl')}
          </Button>
        </Col>
        <Col>
          <Form initialValues={{ ...params }} layout="inline" form={form} onFinish={onSearch}>
            <Form.Item name="keyword">
              <Input.Search
                placeholder={t('dataset.placeholder_name_searchbox')}
                onPressEnter={form.submit}
              />
            </Form.Item>
          </Form>
        </Col>
      </Row>

      <ListContainer>
        {isEmpty ? (
          <NoResult text={t('workflow.no_tpl')} to="/workflow-templates/create/basic" />
        ) : (
          <Table
            loading={listQ.isFetching}
            dataSource={listData}
            columns={columns}
            scroll={{ x: '100%' }}
            rowKey="name"
          />
        )}
      </ListContainer>
    </ListPageLayout>
  );

  function goCreate() {
    history.push('/workflow-templates/create/basic');
  }
  function onSearch(values: any) {
    setParams(values);
  }
  async function onDeleteConfirm(record: WorkflowTemplate) {
    const [, error] = await to(deleteTemplate(record.id));

    if (error) {
      return message.error(error.message);
    }

    listQ.refetch();
  }
};

export default TemplateList;
