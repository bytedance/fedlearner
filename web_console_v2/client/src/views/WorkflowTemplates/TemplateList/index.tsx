import React, { FC, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { Link, Route, useHistory } from 'react-router-dom';
import {
  createWorkflowTemplate,
  deleteTemplate,
  fetchTemplateById,
  fetchWorkflowTemplateList,
  getTemplateDownloadHref,
} from 'services/workflow';
import styled from 'styled-components';
import SharedPageLayout from 'components/SharedPageLayout';
import NoResult from 'components/NoResult';
import {
  Col,
  Input,
  Row,
  Table,
  Form,
  Button,
  Tag,
  Popconfirm,
  message,
  Dropdown,
  Menu,
} from 'antd';
import { WorkflowTemplate, WorkflowTemplatePayload } from 'typings/workflow';
import GridRow from 'components/_base/GridRow';
import { to } from 'shared/helpers';
import { useToggle } from 'react-use';
import { forceToRefreshQuery } from 'shared/queryClient';
import { CloudUploadOutlined } from '@ant-design/icons';
import TemplateUploadDialog from './TemplateUploadDialog';
import request from 'libs/request';
import { saveBlob } from 'shared/helpers';

const ListContainer = styled.div`
  display: flex;
  flex: 1;
  width: 100%;
`;
const UploadMenuItem = styled(Menu.Item)`
  width: 150;
  padding: 10px 15px;
`;
const TemplateName = styled(Link)`
  font-size: 16px;
`;

export const TPL_LIST_QUERY_KEY = 'fetchTemplateList';

const DownloadTemplate: FC<{ template: WorkflowTemplate }> = ({ template: { id, name } }) => {
  const { t } = useTranslation();

  return (
    <Button type="link" size="small" onClick={onClick}>
      {t('workflow.action_download')}
    </Button>
  );

  async function onClick() {
    try {
      const blob = await request(getTemplateDownloadHref(id), {
        responseType: 'blob',
      });
      saveBlob(blob, `${name}.json`);
    } catch (error) {
      message.error(error.message);
    }
  }
};

const DuplicateTemplate: FC<{ template: WorkflowTemplate }> = ({ template: { id } }) => {
  const { t } = useTranslation();

  const [loading, setLoading] = useToggle(false);

  return (
    <Button type="link" size="small" loading={loading} onClick={onClick}>
      {t('workflow.action_fork')}
    </Button>
  );

  async function onClick() {
    setLoading(true);
    const [res, err] = await to(fetchTemplateById(id));
    setLoading(false);

    if (err) {
      return message.error(t('workflow.msg_get_tpl_detail_failed'));
    }

    const newTplPayload: WorkflowTemplatePayload = res.data;
    newTplPayload.name = res.data.name + '-copy';

    const [, error] = await to(createWorkflowTemplate(newTplPayload));

    if (error) {
      return message.error(error.message);
    }

    forceToRefreshQuery(TPL_LIST_QUERY_KEY);
  }
};

const TemplateList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [form] = Form.useForm();
  const [params, setParams] = useState({ keyword: '' });

  const listQ = useQuery(TPL_LIST_QUERY_KEY, () => fetchWorkflowTemplateList(), {
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
            <GridRow left="-10" gap="8">
              <DownloadTemplate template={record} />

              <DuplicateTemplate template={record} />

              <Button size="small" type="link">
                <Link to={`/workflow-templates/edit/basic/${record.id}`}>{t('edit')}</Link>
              </Button>

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t],
  );

  return (
    <>
      <Route path="/workflow-templates/upload" exact component={TemplateUploadDialog} />

      <SharedPageLayout title={t('menu.label_workflow_tpl')} tip="This feature is experimental">
        <Row gutter={16} justify="space-between" align="middle">
          <Col>
            <Dropdown.Button
              placement="bottomCenter"
              overlay={
                <Menu>
                  <UploadMenuItem key="1" icon={<CloudUploadOutlined />} onClick={onUploadClick}>
                    {t('workflow.btn_upload_tpl')}
                  </UploadMenuItem>
                </Menu>
              }
              size="large"
              type="primary"
              onClick={goCreate}
            >
              {t('workflow.create_tpl')}
            </Dropdown.Button>
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
      </SharedPageLayout>
    </>
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
  async function onUploadClick() {
    history.push('/workflow-templates/upload');
  }
};

export default TemplateList;
