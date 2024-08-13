import React, { FC, useMemo, useState } from 'react';
import { generatePath, Link, Route, useHistory } from 'react-router-dom';
import styled from './index.module.less';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';

import request from 'libs/request';
import {
  deleteTemplate,
  fetchWorkflowTemplateList,
  getTemplateDownloadHref,
} from 'services/workflow';

import { useIsAdminRole } from 'hooks/user';
import { useUrlState } from 'hooks';
import { saveBlob } from 'shared/helpers';
import { TIME_INTERVAL } from 'shared/constants';
import { useGetIsCanEditTemplate } from 'views/WorkflowTemplates/shared';
import routeMaps, { WorkflowTemplateDetailTab } from '../routes';

import { Table, Grid, Input, Tag, Message, Dropdown, Menu, Tabs } from '@arco-design/web-react';
import { IconUpload } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import NoResult from 'components/NoResult';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';
import MoreActions, { ActionItem } from 'components/MoreActions';
import Modal from 'components/Modal';
import TemplateUploadDialog from './TemplateUploadDialog';
import CopyFormModal from './CopyFormModal';

import { WorkflowTemplate, WorkflowTemplateMenuType } from 'typings/workflow';
import { FilterOp } from 'typings/filter';
import { constructExpressionTree, expression2Filter } from 'shared/filter';

const Row = Grid.Row;
const Col = Grid.Col;

type QueryParams = {
  name?: string;
  kind?: string;
};

export const TPL_LIST_QUERY_KEY = 'fetchTemplateList';
export const KIND_VALUE_MAPPER: Record<WorkflowTemplateMenuType, number> = {
  [WorkflowTemplateMenuType.MY]: 0,
  [WorkflowTemplateMenuType.BUILT_IN]: 1,
  [WorkflowTemplateMenuType.PARTICIPANT]: 2,
};

const TemplateList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [isShowCopyFormModal, setIsShowCopyFormModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate>();

  const isAdminRole = useIsAdminRole();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: initFilter(),
    tab: WorkflowTemplateMenuType.MY,
  });

  const initFilterParams = expression2Filter(urlState.filter);
  const [filterParams, setFilterParams] = useState<QueryParams>({
    name: initFilterParams.name || '',
    kind: initFilterParams.kind || urlState.tab,
  });
  const { isCanEdit } = useGetIsCanEditTemplate(urlState.tab === WorkflowTemplateMenuType.BUILT_IN);

  const listQ = useQuery(
    [TPL_LIST_QUERY_KEY, urlState],
    () =>
      fetchWorkflowTemplateList({
        page: urlState.page,
        pageSize: urlState.pageSize,
        filter: urlState.filter,
      }),
    {
      refetchOnWindowFocus: false,
      keepPreviousData: true,
      refetchInterval: TIME_INTERVAL.LIST,
    },
  );

  // Filter the display list by the search string
  const templateListShow = useMemo(() => {
    if (!listQ.data?.data) {
      return [];
    }
    const templateList = listQ.data.data || [];
    return templateList;
  }, [listQ.data]);

  const columns = useMemo(
    () => {
      const tempColumns = [
        {
          title: '模板名',
          dataIndex: 'name',
          name: 'name',
          render: (name: string, record: WorkflowTemplate) => (
            <GridRow gap={8}>
              <Link className={styled.template_name} to={gotoTemplateDetail(record)}>
                {name}
              </Link>
              {record.is_local && <Tag color={'cyan'}>单侧</Tag>}
            </GridRow>
          ),
        },
        {
          title: 'Group 别名',
          dataIndex: 'group_alias',
          name: 'group_alias',
        },
        {
          title: '创建方',
          dataIndex: 'coordinator_pure_domain_name',
          name: 'coordinator_pure_domain_name',
          render: (value: any) => <span>{value || '-'}</span>,
        },
        {
          title: '操作',
          dataIndex: 'operation',
          name: 'operation',
          width: 200,
          render: (_: any, record: WorkflowTemplate) => {
            const isInBuiltInTab = urlState.tab === WorkflowTemplateMenuType.BUILT_IN;

            const isShowEditButton =
              isCanEdit && urlState.tab !== WorkflowTemplateMenuType.PARTICIPANT;

            const actionList = [
              {
                label: '下载',
                onClick: async () => {
                  const { id, name } = record;
                  try {
                    const blob = await request(getTemplateDownloadHref(id), {
                      responseType: 'blob',
                    });
                    saveBlob(blob, `${name}.json`);
                  } catch (error: any) {
                    Message.error(error.message);
                  }
                },
              },
              !isInBuiltInTab && {
                label: '复制',
                onClick: () => {
                  setIsShowCopyFormModal((prevState) => true);
                  setSelectedTemplate((prevState) => record);
                },
              },
              !isInBuiltInTab && {
                label: '删除',
                onClick: () => {
                  Modal.delete({
                    title: `确认删除${record.name || ''}吗?`,
                    content: '删除后，该模板将无法进行操作，请谨慎删除',
                    onOk() {
                      deleteTemplate(record.id)
                        .then(() => {
                          Message.success('删除成功');
                          listQ.refetch();
                        })
                        .catch((error) => {
                          Message.error(error.message);
                        });
                    },
                  });
                },
                danger: true,
              },
            ].filter(Boolean) as ActionItem[];

            return (
              <GridRow left={isShowEditButton ? '-10' : '0'} gap="8">
                {isShowEditButton && (
                  <Link to={`/workflow-center/workflow-templates/edit/basic/${record.id}`}>
                    编辑
                  </Link>
                )}
                <MoreActions actionList={actionList} />
              </GridRow>
            );
          },
        },
      ];
      if (urlState.tab !== WorkflowTemplateMenuType.PARTICIPANT) {
        tempColumns.splice(2, 1);
      }
      return tempColumns;
    },

    // eslint-disable-next-line react-hooks/exhaustive-deps
    [listQ, isAdminRole, urlState.tab, isCanEdit],
  );

  const isEmpty = templateListShow.length === 0;
  const isInBuiltInTab = urlState.tab !== WorkflowTemplateMenuType.MY;

  return (
    <>
      <Route
        path={`/workflow-center/workflow-templates/upload`}
        exact
        component={TemplateUploadDialog}
      />

      <SharedPageLayout
        title="模板管理"
        tip="创建工作流时需要依赖于模板，模板用于定义工作流流程与参数。"
      >
        <RemovePadding style={{ height: 46 }}>
          <Tabs activeTab={urlState.tab} onChange={onTabChange}>
            <Tabs.TabPane
              title={t('workflow.label_tab_workflow_tpl_my')}
              key={WorkflowTemplateMenuType.MY}
            />
            <Tabs.TabPane
              title={t('workflow.label_tab_workflow_tpl_built_in')}
              key={WorkflowTemplateMenuType.BUILT_IN}
            />
            <Tabs.TabPane title={'合作伙伴模版'} key={WorkflowTemplateMenuType.PARTICIPANT} />
          </Tabs>
        </RemovePadding>
        <Row justify="space-between" align="center">
          <Col flex={6}>
            {!isInBuiltInTab && (
              <Dropdown.Button
                className="custom-operation-button"
                type="primary"
                position="bottom"
                droplist={
                  <Menu>
                    <Menu.Item className={styled.upload_menu_item} key="1" onClick={onUploadClick}>
                      <IconUpload />
                      上传模板
                    </Menu.Item>
                  </Menu>
                }
                onClick={goCreate}
              >
                创建模板
              </Dropdown.Button>
            )}
          </Col>
          <Col flex="200px">
            <Input.Search
              className="custom-input"
              defaultValue={filterParams.name}
              placeholder="请输入模板名搜索"
              onSearch={onSearch}
              allowClear
            />
          </Col>
        </Row>
        <div className={styled.list_container}>
          {isEmpty ? (
            <NoResult text="暂无工作流模板" to="/workflow-center/workflow-templates/create/basic" />
          ) : (
            <Table
              className="custom-table custom-table-left-side-filter"
              loading={listQ.isFetching}
              data={templateListShow}
              columns={columns}
              scroll={{ x: '100%' }}
              rowKey="id"
              pagination={{
                total: listQ.data?.page_meta?.total_items ?? undefined,
                current: Number(urlState.page),
                pageSize: Number(urlState.pageSize),
                onChange: onPageChange,
                showTotal: (total: number) => `共 ${total} 条记录`,
              }}
            />
          )}
        </div>
        <CopyFormModal
          selectedWorkflowTemplate={selectedTemplate}
          initialValues={{
            name: selectedTemplate ? `${selectedTemplate.name}${t('workflow.copy')}` : undefined,
          }}
          visible={isShowCopyFormModal}
          onSuccess={onCopyFormModalSuccess}
          onCancel={onCopyFormModalClose}
        />
      </SharedPageLayout>
    </>
  );

  function goCreate() {
    history.push('/workflow-center/workflow-templates/create/basic');
  }
  function onSearch(val: any) {
    setFilterParams({
      name: val,
    });
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
    }));
    constructFilterArray({ ...filterParams, name: val });
  }
  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }
  function onUploadClick() {
    history.push(`/workflow-center/workflow-templates/upload`);
  }
  function onCopyFormModalSuccess() {
    setIsShowCopyFormModal((prevState) => false);
    listQ.refetch();
  }
  function onCopyFormModalClose() {
    setIsShowCopyFormModal((prevState) => false);
    setSelectedTemplate((prevState) => undefined);
  }
  function onTabChange(val: string) {
    setUrlState((prevState) => ({
      ...prevState,
      tab: val,
    }));
    constructFilterArray({ ...filterParams, kind: val });
  }
  function gotoTemplateDetail(record: any) {
    return generatePath(routeMaps.WorkflowTemplateDetail, {
      id: record.id,
      tab: 'config' as WorkflowTemplateDetailTab,
      templateType: urlState.tab,
    });
  }
  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];
    if (value.kind) {
      expressionNodes.push({
        field: 'kind',
        op: FilterOp.EQUAL,
        number_value: KIND_VALUE_MAPPER?.[value.kind as WorkflowTemplateMenuType],
      });
    }
    if (value.name) {
      expressionNodes.push({
        field: 'name',
        op: FilterOp.CONTAIN,
        string_value: value.name,
      });
    }

    const serialization = constructExpressionTree(expressionNodes);
    setFilterParams({
      name: value.name,
      kind: value.kind,
    });
    setUrlState((prevState) => ({
      ...prevState,
      filter: serialization,
      tab: value.kind,
      page: 1,
    }));
  }
  function initFilter() {
    const expressionNodes = [];
    expressionNodes.push({
      field: 'kind',
      op: FilterOp.EQUAL,
      number_value: 0,
    });
    return constructExpressionTree(expressionNodes);
  }
};

export default TemplateList;
