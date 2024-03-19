import React, { FC, useState, useEffect, useMemo } from 'react';
import styled from './index.module.less';
import {
  Form,
  Select,
  Radio,
  Button,
  Input,
  Spin,
  Card,
  Notification,
  Message,
  Alert,
} from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import GridRow from 'components/_base/GridRow';
import { useHistory, useLocation, useParams, Link } from 'react-router-dom';
import {
  CreateWorkflowBasicForm,
  workflowBasicForm,
  workflowInEditing,
  workflowConfigForm,
  peerConfigInPairing,
  templateInUsing,
} from 'stores/workflow';
import { useRecoilState, useSetRecoilState } from 'recoil';
import { useRecoilQuery } from 'hooks/recoil';
import { Workflow, WorkflowConfig, WorkflowTemplate } from 'typings/workflow';
import { projectListQuery } from 'stores/project';
import { useQuery } from 'react-query';
import {
  fetchWorkflowTemplateList,
  getPeerWorkflowsConfig,
  getWorkflowDetailById,
  fetchTemplateById,
  PEER_WORKFLOW_DETAIL_QUERY_KEY,
  fetchRevisionList,
  fetchRevisionDetail,
} from 'services/workflow';
import { parseComplexDictField } from 'shared/formSchema';
import { to } from 'shared/helpers';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import ScheduledWorkflowRunning, {
  scheduleIntervalValidator,
} from 'views/Workflows/ScheduledWorkflowRunning';
import FormLabel from 'components/FormLabel';
import Modal from 'components/Modal';
import { parseSearch } from 'shared/url';
import { useIsFormValueChange } from 'hooks';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { FilterOp } from 'typings/filter';
import { constructExpressionTree } from 'shared/filter';

type FilterParams = {
  groupAlias?: string;
};

const WorkflowsEditStepOne: FC<{
  onFormValueChange?: () => void;
}> = ({ onFormValueChange: onFormValueChangeFromProps }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const location = useLocation();
  const params = useParams<{ id: string }>();

  const [groupAlias, setGroupAlias] = useState('');
  const [tplId, setTplId] = useState(0);

  const [formInstance] = Form.useForm<CreateWorkflowBasicForm>();

  const { data: projectList } = useRecoilQuery(projectListQuery);
  const [formData, setFormData] = useRecoilState(workflowBasicForm);
  const [currTemplate, setTemplateInUsing] = useRecoilState(templateInUsing);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [workflowConfig, setWorkflowConfigForm] = useRecoilState(workflowConfigForm);
  const setPeerConfig = useSetRecoilState(peerConfigInPairing);

  // Using when Participant accept the initiation
  // it should be null if it's Coordinator side initiate a workflow
  const [workflow, setWorkflow] = useRecoilState(workflowInEditing);

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    // Only do workflow fetch if:
    // 1. id existed in url
    // 2. workflow on store is null (i.e. user landing here not from workflow list)
    enabled: Boolean(params.id) && !Boolean(workflow),
    refetchOnWindowFocus: false,
  });

  const isLocalWorkflow = workflow?.is_local;

  const peerWorkflowQuery = useQuery([PEER_WORKFLOW_DETAIL_QUERY_KEY, params.id], getPeerWorkflow, {
    enabled: Boolean(params.id) && !isLocalWorkflow && !workflowQuery.isFetching,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const tplListQuery = useQuery(
    ['getTemplateList', groupAlias],
    async () =>
      fetchWorkflowTemplateList({
        filter: constructFilterExpression({ groupAlias }),
      }),
    {
      enabled: Boolean(!!peerWorkflowQuery.data && groupAlias) || isLocalWorkflow,
      refetchOnWindowFocus: false,
    },
  );

  const revisionListQuery = useQuery(['getRevisionList', tplId], () => fetchRevisionList(tplId), {
    enabled: Boolean(tplId),
    refetchOnWindowFocus: false,
  });

  const peerErrorMsg = (peerWorkflowQuery.error as Error)?.message;

  useEffect(() => {
    if (peerErrorMsg) {
      Notification.error({
        title: t('workflow.msg_peer_config_failed'),
        content: `${peerErrorMsg} ${t('pls_try_again_later')}`,
        duration: 0,
      });
    }
  }, [peerErrorMsg, t]);

  const tplList = tplListQuery.data?.data || [];
  const noAvailableTpl = tplList.length === 0;

  const revisionList = useMemo(() => {
    if (!revisionListQuery.data) return [];
    return revisionListQuery.data?.data || [];
  }, [revisionListQuery.data]);

  const noAvailableRevision = revisionList.length === 0;

  const projectId = Number(parseSearch(location).get('project')) || undefined;
  const initValues = _getInitialValues(formData, workflow, projectId);

  const pairingPrefix = 'pairing_';

  return (
    <Card bordered={false} className={styled.container}>
      <Spin loading={workflowQuery.isLoading} style={{ width: '100%' }}>
        <div className={styled.form_container}>
          {isLocalWorkflow && (
            <Alert
              className={styled.local_alert}
              type="info"
              content="该任务为本地任务，仅支持单侧模板选择"
              banner
            />
          )}
          <Form
            labelCol={{ span: 6 }}
            wrapperCol={{ span: 18 }}
            form={formInstance}
            onValuesChange={onFormValueChange}
            initialValues={initValues}
          >
            <Form.Item
              field="name"
              hasFeedback
              label={t('workflow.label_name')}
              rules={[
                { required: true, message: t('workflow.msg_name_required') },
                { max: 255, message: t('workflow.msg_workflow_name_invalid') },
              ]}
            >
              <Input disabled placeholder={t('workflow.placeholder_name')} />
            </Form.Item>

            <Form.Item
              field="project_id"
              label={t('workflow.label_project')}
              hasFeedback
              rules={[{ required: true, message: t('workflow.msg_project_required') }]}
            >
              <Select disabled placeholder={t('workflow.placeholder_project')}>
                {projectList &&
                  projectList.map((pj) => (
                    <Select.Option key={pj.id} value={pj.id}>
                      {pj.name}
                    </Select.Option>
                  ))}
              </Select>
            </Form.Item>

            <Form.Item field="_keepUsingOriginalTemplate" label={t('workflow.label_template')}>
              <Radio.Group type="button">
                <Radio value={true}>{t('workflow.label_use_original_tpl')}</Radio>
                <Radio value={false}>{t('workflow.label_choose_new_tpl')}</Radio>
              </Radio.Group>
            </Form.Item>

            {!formData._keepUsingOriginalTemplate && (
              <>
                <Form.Item
                  wrapperCol={{ offset: 6 }}
                  field="_templateSelected"
                  hasFeedback
                  rules={[{ required: true, message: t('workflow.msg_template_required') }]}
                >
                  {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
                    <span className={styled.no_available_tpl}>
                      {t(`workflow.msg_${pairingPrefix}no_abailable_tpl`)}
                    </span>
                  ) : (
                    <Select
                      loading={tplListQuery.isLoading}
                      disabled={Boolean(tplListQuery.error)}
                      onChange={onTemplateSelectChange}
                      placeholder={t('workflow.placeholder_template')}
                      showSearch
                      allowClear
                      filterOption={(inputValue, option) =>
                        option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                      }
                    >
                      {tplList.map((tpl) => (
                        <Select.Option key={tpl.id} value={tpl.id}>
                          {tpl.name}
                        </Select.Option>
                      ))}
                    </Select>
                  )}
                </Form.Item>

                <Form.Item
                  wrapperCol={{ offset: 6 }}
                  style={{ marginBottom: 0, marginTop: '-10px' }}
                >
                  <Link
                    to="/workflow-center/workflow-templates/create/basic"
                    style={{ fontSize: '12px' }}
                  >
                    {t('workflow.btn_go_create_new_tpl')}
                  </Link>
                </Form.Item>

                {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
                  <></>
                ) : (
                  <Form.Item
                    wrapperCol={{ offset: 6 }}
                    field="_revisionSelected"
                    hasFeedback
                    // rules={[{ required: true, message: t('workflow.msg_revision_required') }]}
                  >
                    <Select
                      loading={revisionListQuery.isLoading}
                      disabled={Boolean(revisionListQuery.error || noAvailableRevision)}
                      onChange={onRevisionSelectChange}
                      placeholder={t('workflow.placeholder_revision')}
                      showSearch
                      allowClear
                      filterOption={(inputValue, option) =>
                        option.props.children
                          .join('')
                          .toLowerCase()
                          .indexOf(inputValue.toLowerCase()) >= 0
                      }
                    >
                      {revisionList?.map((revision) => (
                        <Select.Option key={revision.id} value={revision.id}>
                          V{revision.revision_index}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                )}
              </>
            )}

            {renderForkableItem()}

            <Form.Item
              field="cron_config"
              label={
                <FormLabel
                  label={t('workflow.label_enable_batch_update_interval')}
                  tooltip={t('workflow.msg_schduled_run')}
                />
              }
              rules={[
                {
                  validator: scheduleIntervalValidator,
                  message: t('workflow.msg_time_required'),
                  validateTrigger: 'onSubmit',
                },
              ]}
            >
              <ScheduledWorkflowRunning />
            </Form.Item>
          </Form>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16} top="12">
              <Button type="primary" htmlType="submit" onClick={onNextStepClick}>
                {t('next_step')}
              </Button>

              <ButtonWithModalConfirm onClick={backToList} isShowConfirmModal={isFormValueChanged}>
                {t('cancel')}
              </ButtonWithModalConfirm>
            </GridRow>
          </Form.Item>
        </div>
      </Spin>
    </Card>
  );

  function goNextStep() {
    history.push(`/workflow-center/workflows/edit/config/${params.id}`);
  }
  function backToList() {
    // if new tab only open this page，no other page has been opened，then go to workflows list page
    if (history.length <= 2) {
      history.push('/workflow-center/workflows');
      return;
    }
    history.go(-1);
  }
  function setCurrentUsingTemplate(tpl?: WorkflowTemplate<any>) {
    if (!tpl) {
      setTemplateInUsing(null as any);
      return;
    }
    // Widget schemas of the template from backend side are JSON-string type
    // parse it before using
    const parsedTpl = parseComplexDictField(tpl);
    // For flow chart render
    setTemplateInUsing(parsedTpl);
    // For initiate workflow config's data
    setWorkflowConfigForm(parsedTpl.config as WorkflowConfig<JobNodeRawData>);
  }
  async function getWorkflowDetail() {
    let { data } = await getWorkflowDetailById(params.id);
    data = parseComplexDictField(data);

    setWorkflow(data);
    setWorkflowConfigForm(data.config as WorkflowConfig<JobNodeRawData>);
    formInstance.setFieldsValue((data as any) as CreateWorkflowBasicForm);
    setFormData({
      ...formData,
      cron_config: data.cron_config,
    });
  }
  async function getPeerWorkflow() {
    const res = await getPeerWorkflowsConfig(params.id);

    const anyPeerWorkflow = parseComplexDictField(
      Object.values(res.data).find((item) => Boolean(item.uuid))!,
    )!;

    setPeerConfig(anyPeerWorkflow.config ?? (undefined as never));
    setGroupAlias(anyPeerWorkflow.config?.group_alias || '');

    return anyPeerWorkflow;
  }
  // --------- Handlers -----------
  function constructFilterExpression(value: FilterParams) {
    const expressionNodes = [];
    if (value.groupAlias) {
      expressionNodes.push({
        field: 'group_alias',
        op: FilterOp.EQUAL,
        string_value: value.groupAlias,
      });
    }

    return constructExpressionTree(expressionNodes);
  }

  function onFormChange(_: any, values: CreateWorkflowBasicForm) {
    onFormValueChangeFromProps?.();
    setFormData(values);
  }
  async function onTemplateSelectChange(id: number) {
    formInstance.setFieldsValue({ _revisionSelected: undefined });
    if (!id) {
      // If user clear select
      setCurrentUsingTemplate(undefined);
      setTplId(0);
      return;
    }

    setTplId(id);
    const [res, error] = await to(fetchTemplateById(id));

    if (error) {
      Message.error(t('workflow.msg_get_tpl_detail_failed'));
      return;
    }
    if (!res.data) return;
    setCurrentUsingTemplate(res.data);
  }

  async function onRevisionSelectChange(revision_id: number) {
    // fetch revision detail
    if (!revision_id) return;

    const [res, error] = await to(fetchRevisionDetail(revision_id));

    if (error) {
      Message.error(t('workflow.msg_get_revision_detail_failed'));
      return;
    }

    setCurrentUsingTemplate({
      ...currTemplate,
      revision_id,
      config: res.data.config,
      editor_info: res.data.editor_info,
    });
  }

  async function onNextStepClick() {
    if (
      (!formData.cron_config && !initValues.cron_config) ||
      formData.cron_config === initValues.cron_config
    ) {
      setFormData({
        ...formData,
        cron_config: undefined,
      });
    }
    try {
      // Any form invalidation happens will throw error to stop the try block
      await formInstance.validate();

      if (formData._keepUsingOriginalTemplate) {
        goNextStep();
        return;
      }

      Modal.confirm({
        title: t('workflow.msg_sure_2_replace_tpl'),
        content: t('workflow.msg_loose_origin_vars_vals'),
        onOk() {
          goNextStep();
        },
      });
    } catch {
      /** ignore validation error */
    }
  }

  // ---------- Renders --------
  function renderForkableItem() {
    if (isLocalWorkflow) {
      return null;
    }

    return (
      <Form.Item field="forkable" label={t('workflow.label_peer_forkable')}>
        <Radio.Group type="button">
          <Radio value={true}>{t('workflow.label_allow')}</Radio>
          <Radio value={false}>{t('workflow.label_not_allow')}</Radio>
        </Radio.Group>
      </Form.Item>
    );
  }
};

function _getInitialValues(form: CreateWorkflowBasicForm, workflow: Workflow, projectId?: number) {
  return Object.assign(
    {
      ...form,
    },
    // When user landing from clicking create workflow button
    // in Project page, hydrate project_ud
    projectId ? { project_id: projectId } : null,
    workflow,
  );
}

export default WorkflowsEditStepOne;
