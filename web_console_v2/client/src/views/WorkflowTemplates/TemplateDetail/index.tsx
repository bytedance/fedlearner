import React, { FC, useMemo, useState } from 'react';
import styled from './index.module.less';
import { useTranslation } from 'react-i18next';
import { generatePath, useHistory, useParams } from 'react-router';

import { Spin, Grid, Button, Space, Tabs, Message, Modal } from '@arco-design/web-react';
import { useGetIsCanEditTemplate } from '../shared';
import SharedPageLayout from 'components/SharedPageLayout';
import BreadcrumbLink from 'components/BreadcrumbLink';

import request from 'libs/request';
import { saveBlob } from 'shared/helpers';
import CONSTANTS from 'shared/constants';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import TemplateConfig from '../TemplateConfig';
import WorkflowList from './WorkflowList';
import RevisionList from './RevisionList';
import routes, { WorkflowTemplateDetailParams, WorkflowTemplateDetailTab } from '../routes';
import { Rocket } from 'components/IconPark';

import {
  deleteTemplate,
  fetchRevisionDetail,
  fetchTemplateById,
  getTemplateDownloadHref,
} from 'services/workflow';
import { useQuery } from 'react-query';
import { parseComplexDictField } from 'shared/formSchema';
import {
  definitionsStore,
  editorInfosStore,
  JobDefinitionForm,
  preprocessVariables,
  TPL_GLOBAL_NODE_UUID,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { giveWeakRandomKey } from 'shared/helpers';
import { omit } from 'lodash-es';
import { JobSlotReferenceType, WorkflowTemplate, WorkflowTemplateMenuType } from 'typings/workflow';
import {
  parseOtherJobRef,
  parseSelfRef,
  parseWorkflowRef,
} from '../TemplateConfig/JobComposeDrawer/SloEntrytList/helpers';
import { useRecoilState } from 'recoil';
import { templateForm } from 'stores/template';
import CopyFormModal from '../TemplateList/CopyFormModal';
import { formatTimestamp } from 'shared/date';
import { Job } from 'typings/job';
import { Variable } from 'typings/variable';
import { useUnmount } from 'react-use';
import { useResetCreateForm } from 'hooks/template';

const Row = Grid.Row;
const Col = Grid.Col;

const TemplateDetail: FC = () => {
  const { t } = useTranslation();
  const params = useParams<WorkflowTemplateDetailParams>();
  const history = useHistory();
  const reset = useResetCreateForm();
  const [template, setTemplateForm] = useRecoilState(templateForm);
  const [collapsed, setCollapsed] = useState(true);
  const [isShowCopyFormModal, setIsShowCopyFormModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate>();
  const [revisionId, setRevisionId] = useState(0);
  const { isCanEdit } = useGetIsCanEditTemplate(
    params.templateType === WorkflowTemplateMenuType.BUILT_IN,
  );
  const templateQuery = useQuery(
    ['fetchTemplateById', params.id],
    () => {
      return fetchTemplateById(params.id);
    },
    {
      retry: 1,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        onQuerySuccess(res.data);
      },
    },
  );

  const templateDetail = useMemo(() => {
    if (!templateQuery.data?.data) return undefined;
    return templateQuery.data.data;
  }, [templateQuery.data]);

  const revisionQuery = useQuery(
    ['fetchRevisionDetail', revisionId, templateDetail],
    () => {
      return fetchRevisionDetail(revisionId);
    },
    {
      retry: 1,
      enabled: templateDetail !== undefined && revisionId !== 0,
      refetchOnWindowFocus: false,
      keepPreviousData: true,
      onSuccess(res) {
        const {
          name,
          kind,
          group_alias,
          created_at,
          updated_at,
          creator_username,
          comment,
          id,
        } = (templateDetail as unknown) as WorkflowTemplate<Job, Variable>;
        const { is_local, config, editor_info } = parseComplexDictField(res.data);
        const revision_id = res.data.id;
        const data: WorkflowTemplate<Job, Variable> = {
          name: name!,
          kind: kind!,
          group_alias: group_alias!,
          created_at,
          updated_at,
          creator_username,
          comment,
          id,
          revision_id,
          is_local,
          config,
          editor_info,
        };
        onQuerySuccess(data);
      },
    },
  );

  const BreadcrumbLinkPaths = useMemo(() => {
    return [
      { label: 'menu.label_workflow_tpl', to: '/workflow-center/workflow-templates' },
      { label: 'workflow.template_detail' },
    ];
  }, []);
  const displayedProps = useMemo(
    () => [
      {
        value: template.group_alias,
        label: t('workflow.col_group_alias'),
      },
      {
        value: template.creator_username,
        label: t('workflow.col_creator'),
      },
      {
        value: template.updated_at
          ? formatTimestamp(template.updated_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('workflow.col_update_time'),
      },
      {
        value: template.created_at
          ? formatTimestamp(template.created_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('workflow.col_create_time'),
      },
    ],
    [template, t],
  );

  useUnmount(() => {
    reset();
    definitionsStore.clearMap();
    editorInfosStore.clearMap();
  });

  return (
    <SharedPageLayout title={<BreadcrumbLink paths={BreadcrumbLinkPaths} />}>
      <Spin loading={templateQuery.isLoading || revisionQuery.isLoading}>
        <div className={styled.padding_container}>
          <Row>
            <Col span={12}>
              <Space size="medium">
                <div
                  className={styled.avatar}
                  data-name={
                    template?.name ? template.name.slice(0, 1) : CONSTANTS.EMPTY_PLACEHOLDER
                  }
                />
                <div>
                  <h3 className={styled.name}>{template?.name ?? '....'}</h3>
                  <Space className={styled.comment}>
                    {template?.comment ?? CONSTANTS.EMPTY_PLACEHOLDER}
                  </Space>
                </div>
              </Space>
            </Col>
            <Col className={styled.header_col} span={12}>
              <Space>
                <Button
                  type="primary"
                  disabled={!template?.name}
                  onClick={() =>
                    history.push(`/workflow-center/workflows/initiate/basic/${params.id}`)
                  }
                >
                  {t('workflow.create_workflow')}
                </Button>
                {params.templateType !== WorkflowTemplateMenuType.PARTICIPANT && (
                  <Button
                    disabled={!template?.name || !isCanEdit}
                    onClick={() =>
                      history.push(`/workflow-center/workflow-templates/edit/basic/${params.id}`)
                    }
                  >
                    编辑
                  </Button>
                )}
                <MoreActions
                  actionList={[
                    {
                      label: t('workflow.action_download'),
                      disabled: !template?.name,
                      onClick: async () => {
                        const { id, name } = template;
                        try {
                          const blob = await request(getTemplateDownloadHref(id!), {
                            responseType: 'blob',
                          });
                          saveBlob(blob, `${name}.json`);
                        } catch (error: any) {
                          Message.error(error.message);
                        }
                      },
                    },
                    {
                      label: t('copy'),
                      disabled: !template?.name,
                      onClick: () => {
                        setIsShowCopyFormModal((prevState) => true);
                      },
                    },
                    {
                      label: t('delete'),
                      danger: true,
                      disabled: !template?.name,
                      onClick: () => {
                        Modal.confirm({
                          title: `确认删除${template.name || ''}吗?`,
                          content: '删除后，该模板将无法进行操作，请谨慎删除',
                          onOk() {
                            deleteTemplate(template.id!)
                              .then(() => {
                                Message.success('删除成功');
                                history.push(
                                  `/workflow-center/workflow-templates?tab=${params.templateType}}`,
                                );
                              })
                              .catch((error: any) => {
                                Message.error(error.message);
                              });
                          },
                        });
                      },
                    },
                  ]}
                />
              </Space>
            </Col>
          </Row>
          <PropertyList cols={6} colProportions={[1, 1, 1, 1]} properties={displayedProps} />
        </div>
        <div className={styled.content}>
          <RevisionList
            id={params.id}
            name={template?.name}
            ownerType={params.templateType}
            collapsed={collapsed}
            setCollapsed={setCollapsed}
            setRevisionId={setRevisionId}
          />
          <Button
            className={styled.template_create}
            type="text"
            size="mini"
            icon={<Rocket />}
            disabled={revisionId === 0}
            onClick={() => {
              history.push(
                `/workflow-center/workflow-templates/edit/basic/${params.id}/${revisionId}`,
              );
            }}
          >
            生成新模板
          </Button>
          <div
            className={styled.tabs_container}
            style={{ width: collapsed ? 'calc(100% - 256px)' : '100%' }}
          >
            <Tabs
              defaultActiveTab={params.tab}
              onChange={(tab) => history.push(getTabPath(tab))}
              style={{ marginBottom: 0 }}
            >
              <Tabs.TabPane
                title={t('workflow.step_tpl_config')}
                key={WorkflowTemplateDetailTab.Config}
              />
              <Tabs.TabPane
                title={t('workflow.label_workflow_list')}
                key={WorkflowTemplateDetailTab.List}
              />
            </Tabs>
            <div className={styled.padding_container} style={{ paddingTop: 0 }}>
              {params.tab === WorkflowTemplateDetailTab.Config && template.name && (
                <TemplateConfig isCheck={true} revisionId={revisionId} />
              )}
              {params.tab === WorkflowTemplateDetailTab.List && (
                <WorkflowList revisionId={revisionId} />
              )}
            </div>
          </div>
        </div>
      </Spin>
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
  );

  // ------------- Methods ---------------
  function getTabPath(tab: string) {
    return generatePath(routes.WorkflowTemplateDetail, {
      ...params,
      tab: tab as WorkflowTemplateDetailTab,
    });
  }
  function onCopyFormModalSuccess() {
    setIsShowCopyFormModal((prevState) => false);
  }
  function onCopyFormModalClose() {
    setIsShowCopyFormModal((prevState) => false);
    setSelectedTemplate(() => undefined);
  }

  function onQuerySuccess(data: WorkflowTemplate<Job, Variable>) {
    /**
     * Parse the template data from server:
     * 1. basic infos like name, group_alias... write to recoil all the same
     * 2. each job_definition will be tagged with a uuid,
     *    and replace deps souce job name with corresponding uuid,
     *    then the {uuid, dependencies} will save to recoil and real job def values should go ../store.ts
     */
    const {
      name,
      kind,
      group_alias,
      created_at,
      updated_at,
      creator_username,
      comment,
      id,
      is_local,
      config,
      editor_info,
      revision_id,
    } = parseComplexDictField(data);
    setSelectedTemplate(data);
    definitionsStore.upsertValue(TPL_GLOBAL_NODE_UUID, {
      variables: config.variables.map(preprocessVariables),
    } as JobDefinitionForm);
    /**
     * 1. Genrate a Map<uuid, job-name>
     * 2. upsert job definition values to store
     *  - need to stringify code type variable's value
     */
    const nameToUuidMap = config.job_definitions.reduce((map, job) => {
      const thisJobUuid = giveWeakRandomKey();
      map[job.name] = thisJobUuid;

      const value = omit(job, 'dependencies') as JobDefinitionForm;
      value.variables = value.variables.map(preprocessVariables);
      // Save job definition values to definitionsStore
      definitionsStore.upsertValue(thisJobUuid, { ...value });

      return map;
    }, {} as Record<string, string>);
    /**
     * Convert job & variable name in reference to
     * job & variable's UUID we assign above
     */
    config.job_definitions.forEach((job) => {
      const jobUuid = nameToUuidMap[job.name];
      const self = definitionsStore.getValueById(jobUuid)!;

      // Save job editor info to editorInfosStore
      const targetEditInfo = editor_info?.yaml_editor_infos[job.name];

      if (targetEditInfo) {
        editorInfosStore.upsertValue(jobUuid, {
          slotEntries: Object.entries(targetEditInfo.slots)
            .sort()
            .map(([slotName, slot]) => {
              if (slot.reference_type === JobSlotReferenceType.OTHER_JOB) {
                const [jobName, varName] = parseOtherJobRef(slot.reference);
                const targetJobUuid = nameToUuidMap[jobName];
                const target = definitionsStore.getValueById(targetJobUuid);

                if (target) {
                  slot.reference = slot.reference
                    .replace(jobName, targetJobUuid)
                    .replace(
                      varName,
                      target.variables.find((item) => item.name === varName)?._uuid!,
                    );
                }
              }

              if (slot.reference_type === JobSlotReferenceType.JOB_PROPERTY) {
                const [jobName] = parseOtherJobRef(slot.reference);
                const targetJobUuid = nameToUuidMap[jobName];
                const target = definitionsStore.getValueById(targetJobUuid);

                if (target) {
                  slot.reference = slot.reference.replace(jobName, targetJobUuid);
                }
              }

              if (slot.reference_type === JobSlotReferenceType.SELF) {
                const varName = parseSelfRef(slot.reference);

                slot.reference = slot.reference.replace(
                  varName,
                  self.variables.find((item) => item.name === varName)?._uuid!,
                );
              }

              if (slot.reference_type === JobSlotReferenceType.WORKFLOW) {
                const varName = parseWorkflowRef(slot.reference);
                const globalDef = definitionsStore.getValueById(TPL_GLOBAL_NODE_UUID)!;

                slot.reference = slot.reference.replace(
                  varName,
                  globalDef.variables.find((item) => item.name === varName)?._uuid!,
                );
              }

              return [slotName, slot];
            }),
          meta_yaml: targetEditInfo.meta_yaml,
        });
      } else {
        editorInfosStore.insertNewResource(jobUuid);
      }
    });

    const jobNodeSlimRawDataList = config.job_definitions.map((job) => {
      const uuid = nameToUuidMap[job.name];

      return {
        uuid,
        dependencies: job.dependencies.map((dep) => ({ source: nameToUuidMap[dep.source] })),
      };
    });
    setTemplateForm({
      id,
      revision_id,
      name,
      comment,
      is_local,
      group_alias,
      config: {
        variables: [],
        job_definitions: jobNodeSlimRawDataList,
      },
      kind,
      created_at,
      updated_at,
      creator_username,
    });
  }
};

export default TemplateDetail;
