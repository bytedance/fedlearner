import React, { FC, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Input,
  Message,
  Notification,
  Radio,
  Select,
  Spin,
  Typography,
  Form,
} from '@arco-design/web-react';
import styled from './index.module.less';
import FormLabel from 'components/FormLabel';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { useRecoilQuery } from 'hooks/recoil';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { useHistory, useLocation, useParams } from 'react-router-dom';
import { useToggle } from 'react-use';
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil';
import {
  fetchRevisionDetail,
  fetchRevisionList,
  fetchTemplateById,
  fetchWorkflowTemplateList,
  getPeerWorkflowsConfig,
  getWorkflowDetailById,
  PEER_WORKFLOW_DETAIL_QUERY_KEY,
} from 'services/workflow';
import { parseComplexDictField } from 'shared/formSchema';
import { to } from 'shared/helpers';
import { parseSearch } from 'shared/url';
import { validNamePattern, isWorkflowNameUniqWithDebounce } from 'shared/validator';
import { projectListQuery, projectState } from 'stores/project';
import {
  CreateWorkflowBasicForm,
  peerConfigInPairing,
  templateInUsing,
  workflowBasicForm,
  workflowConfigForm,
  workflowInEditing,
} from 'stores/workflow';
import { Workflow, WorkflowConfig, WorkflowTemplate } from 'typings/workflow';
import ScheduledWorkflowRunning, {
  scheduleIntervalValidator,
} from 'views/Workflows/ScheduledWorkflowRunning';
import { WorkflowCreateProps } from '..';
import { useIsFormValueChange } from 'hooks';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { FilterOp } from 'typings/filter';
import { constructExpressionTree } from 'shared/filter';

type FilterParams = {
  groupAlias?: string;
};

const WorkflowsCreateStepOne: FC<WorkflowCreateProps> = ({
  isInitiate,
  isAccept,
  onFormValueChange: onFormValueChangeFromProps,
}) => {
  const { t } = useTranslation();
  const history = useHistory();
  const location = useLocation();
  const params = useParams<{ id: string; template_id?: string }>();
  const [groupAlias, setGroupAlias] = useState('');
  const [tplDetailLoading, toggleTplLoading] = useToggle(false);
  const [revisionDetailLoading, toggleRevisionLoading] = useToggle(false);

  const [formInstance] = Form.useForm<CreateWorkflowBasicForm>();

  const { data: projectList } = useRecoilQuery(projectListQuery);
  const project = useRecoilValue(projectState);
  const [formData, setFormData] = useRecoilState(workflowBasicForm);
  const [currTemplate, setTemplateInUsing] = useRecoilState(templateInUsing);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [workflowConfig, setWorkflowConfigForm] = useRecoilState(workflowConfigForm);
  const [tplId, setTplId] = useState(params.template_id || 0);
  const setPeerConfig = useSetRecoilState(peerConfigInPairing);

  // Using when Participant accept the initiation
  // it should be null if it's Coordinator side initiate a workflow
  const [workflow, setWorkflow] = useRecoilState(workflowInEditing);

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    // Only do workflow fetch if:
    // 1. id existed in url
    // 2. in Acceptance mode
    // 3. workflow on store is null (i.e. user landing here not from workflow list)
    enabled: Boolean(params.id) && !!isAccept && !Boolean(workflow),
    refetchOnWindowFocus: false,
  });
  const peerWorkflowQuery = useQuery([PEER_WORKFLOW_DETAIL_QUERY_KEY, params.id], getPeerWorkflow, {
    enabled: Boolean(params.id) && !!isAccept,
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
      enabled: isInitiate || Boolean(!!peerWorkflowQuery.data && groupAlias),
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

  useEffect(() => {
    if (params.template_id) {
      onTemplateSelectChange(Number(params.template_id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tplList = tplListQuery.data?.data || [];
  const noAvailableTpl = tplList.length === 0;

  const revisionList = useMemo(() => {
    if (!revisionListQuery.data) return [];
    return revisionListQuery.data?.data || [];
  }, [revisionListQuery.data]);

  const noAvailableRevision = revisionList.length === 0;
  const projectId =
    project.current?.id ?? Number(parseSearch(location).get('project')) ?? undefined;
  const initValues = params.template_id
    ? _getInitialValues(formData, workflow, projectId, params.template_id)
    : _getInitialValues(formData, workflow, projectId);
  const pairingPrefix = isAccept ? 'pairing_' : '';
  const isLocalRun = currTemplate?.is_local;
  return (
    <Card bordered={false} className={styled.container}>
      <Spin loading={workflowQuery.isLoading} style={{ width: '100%' }}>
        <div className={styled.form_container}>
          <Form
            labelCol={{ span: 6 }}
            wrapperCol={{ span: 18 }}
            form={formInstance}
            onValuesChange={onFormValueChange}
            initialValues={initValues as Partial<CreateWorkflowBasicForm> | undefined}
          >
            <Form.Item
              field="name"
              hasFeedback
              label={t('workflow.label_name')}
              rules={[
                { required: true, message: t('workflow.msg_name_required') },
                { max: 255, message: t('workflow.msg_workflow_name_invalid') },
                { match: validNamePattern, message: t('valid_error.name_invalid') },
                // If isAccept = true, don't check whether workflow name is unique
                !isAccept
                  ? {
                      validator: isWorkflowNameUniqWithDebounce,
                    }
                  : {},
              ]}
            >
              <Input disabled={isAccept} placeholder={t('workflow.placeholder_name')} />
            </Form.Item>

            <Form.Item
              field="project_id"
              label={t('workflow.label_project')}
              hasFeedback
              rules={[{ required: true, message: t('workflow.msg_project_required') }]}
            >
              <Select
                disabled={isAccept}
                placeholder={t('workflow.placeholder_project')}
                showSearch
                allowClear
                filterOption={(inputValue, option) =>
                  option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                }
              >
                {projectList &&
                  projectList.map((pj) => (
                    <Select.Option key={pj.id} value={pj.id}>
                      {pj.name}
                    </Select.Option>
                  ))}
              </Select>
            </Form.Item>

            <Form.Item
              label={t('workflow.label_template')}
              field="_templateSelected"
              hasFeedback
              help={
                isLocalRun ? (
                  <Typography.Text disabled>
                    当前模板仅支持本地运行，无需对侧参与配置
                  </Typography.Text>
                ) : undefined
              }
              rules={[{ required: true, message: t('workflow.msg_template_required') }]}
            >
              {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
                <span className={styled.no_available_tpl}>
                  {t(`workflow.msg_${pairingPrefix}no_abailable_tpl`)}
                </span>
              ) : (
                <Select
                  loading={tplListQuery.isLoading || tplDetailLoading}
                  disabled={Boolean(tplListQuery.error) || noAvailableTpl}
                  onChange={onTemplateSelectChange}
                  placeholder={t('workflow.placeholder_template')}
                  showSearch
                  allowClear
                  filterOption={(inputValue, option) =>
                    option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                  }
                >
                  {tplList?.map((tpl) => (
                    <Select.Option key={tpl.id} value={tpl.id}>
                      {tpl.name}
                    </Select.Option>
                  ))}
                </Select>
              )}
            </Form.Item>

            {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
              <></>
            ) : (
              <Form.Item
                label={t('workflow.label_revision')}
                field="_revisionSelected"
                hasFeedback
                // rules={[{ required: true, message: t('workflow.msg_revision_required') }]}
              >
                <Select
                  loading={revisionListQuery.isLoading || revisionDetailLoading}
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

            <Form.Item
              hidden={isLocalRun}
              field="forkable"
              label={t('workflow.label_peer_forkable')}
            >
              <Radio.Group disabled={isAccept} type="button">
                <Radio value={true}>{t('workflow.label_allow')}</Radio>
                <Radio value={false}>{t('workflow.label_not_allow')}</Radio>
              </Radio.Group>
            </Form.Item>

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

              <ButtonWithModalConfirm
                onClick={backToList}
                isShowConfirmModal={isFormValueChanged || Boolean(formData.name)}
              >
                {t('cancel')}
              </ButtonWithModalConfirm>
            </GridRow>
          </Form.Item>
        </div>
      </Spin>
    </Card>
  );

  async function goNextStep() {
    const nextRoute = isInitiate
      ? '/workflow-center/workflows/initiate/config'
      : `/workflow-center/workflows/accept/config/${params.id}`;
    history.push(nextRoute);
  }
  function backToList() {
    history.push('/workflow-center/workflows');
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
    formInstance.setFieldsValue((data as any) as CreateWorkflowBasicForm);
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
    toggleTplLoading(true);
    const [res, error] = await to(fetchTemplateById(id));
    toggleTplLoading(false);

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

    toggleRevisionLoading(true);
    const [res, error] = await to(fetchRevisionDetail(revision_id));
    toggleRevisionLoading(false);

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
    try {
      // Any form invalidation happens will throw error to stop the try block
      await formInstance.validate();
      goNextStep();
    } catch {
      /** ignore validation error */
    }
  }
};

function _getInitialValues(
  form: CreateWorkflowBasicForm,
  workflow: Workflow,
  projectId?: ID,
  _templateSelected?: ID,
) {
  return Object.assign(
    {
      ...form,
      _templateSelected: Number(_templateSelected) || form._templateSelected,
    },
    // When user landing from clicking create workflow button
    // in Project page, hydrate project_ud
    projectId ? { project_id: projectId } : null,
    workflow,
  );
}

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

export default WorkflowsCreateStepOne;
