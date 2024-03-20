import React, { FC, useState, useEffect } from 'react';
import styled from 'styled-components';
import { Form, Select, Radio, Button, Input, Spin, Card, notification, message } from 'antd';
import { useTranslation } from 'react-i18next';
import GridRow from 'components/_base/GridRow';
import { useHistory, useLocation, useParams } from 'react-router-dom';
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
} from 'services/workflow';
import { WorkflowCreateProps } from '..';
import { parseComplexDictField } from 'shared/formSchema';
import { to } from 'shared/helpers';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import ScheduledWorkflowRunning, {
  scheduleIntervalValidator,
} from 'views/Workflows/ScheduledWorkflowRunning';
import FormLabel from 'components/FormLabel';

const Container = styled(Card)`
  padding-top: 20px;
`;
const StyledForm = styled.div`
  width: 500px;
  margin: 0 auto;
`;
const NoAvailableTpl = styled.span`
  line-height: 32px;
`;

const WorkflowsCreateStepOne: FC<WorkflowCreateProps & { onSuccess?: any }> = ({
  isInitiate,
  isAccept,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const history = useHistory();
  const location = useLocation();
  const params = useParams<{ id: string }>();

  const [groupAlias, setGroupAlias] = useState('');

  const [formInstance] = Form.useForm<CreateWorkflowBasicForm>();

  const { data: projectList } = useRecoilQuery(projectListQuery);
  const [formData, setFormData] = useRecoilState(workflowBasicForm);
  const setTemplateInUsing = useSetRecoilState(templateInUsing);
  const [workflowConfig, setWorkflowConfigForm] = useRecoilState(workflowConfigForm);
  const setPeerConfig = useSetRecoilState(peerConfigInPairing);

  // Using when Participant accept the initiation
  // it should be null if it's Coordinator side initiate a workflow
  const [workflow, setWorkflow] = useRecoilState(workflowInEditing);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    // Only do workflow fetch if:
    // 1. id existed in url
    // 2. in Acceptance mode
    // 3. workflow on store is null (i.e. user landing here not from workflow list)
    enabled: Boolean(params.id) && !!isAccept && !Boolean(workflow),
    refetchOnWindowFocus: false,
  });
  const peerWorkflowQuery = useQuery(['getPeerWorkflow', params.id], getPeerWorkflow, {
    enabled: Boolean(params.id) && !!isAccept,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const allowedIsLeftValue = isInitiate ? 'ALL' : !peerWorkflowQuery.data?.config?.is_left;

  const tplListQuery = useQuery(
    ['getTemplateList', allowedIsLeftValue, groupAlias],
    async () =>
      fetchWorkflowTemplateList({
        isLeft: allowedIsLeftValue === 'ALL' ? undefined : allowedIsLeftValue,
        groupAlias,
      }),
    {
      enabled: isInitiate || Boolean(!!peerWorkflowQuery.data && groupAlias),
      refetchOnWindowFocus: false,
    },
  );

  const peerErrorMsg = (peerWorkflowQuery.error as Error)?.message;
  useEffect(() => {
    if (peerErrorMsg) {
      notification.error({
        message: t('workflow.msg_peer_config_failed'),
        description: `${peerErrorMsg} ${t('pls_try_again_later')}`,
        duration: 0,
      });
    }
  }, [peerErrorMsg, t]);

  const tplList = tplListQuery.data?.data || [];
  const noAvailableTpl = tplList.length === 0;

  const projectId = Number(new URLSearchParams(location.search).get('project')) || undefined;
  const initValues = _getInitialValues(formData, workflow, projectId);

  const pairingPrefix = isAccept ? 'pairing_' : '';

  return (
    <Spin spinning={workflowQuery.isLoading}>
      <Container bordered={false}>
        <StyledForm>
          <Form
            labelCol={{ span: 6 }}
            wrapperCol={{ span: 18 }}
            form={formInstance}
            onValuesChange={onFormChange as any}
            initialValues={initValues}
          >
            <Form.Item
              name="name"
              hasFeedback
              label={t('workflow.label_name')}
              rules={[
                { required: true, message: t('workflow.msg_name_required') },
                { max: 255, message: t('workflow.msg_workflow_name_invalid') },
              ]}
            >
              <Input disabled={isAccept} placeholder={t('workflow.placeholder_name')} />
            </Form.Item>

            <Form.Item
              name="project_id"
              label={t('workflow.label_project')}
              hasFeedback
              rules={[{ required: true, message: t('workflow.msg_project_required') }]}
            >
              <Select disabled={isAccept} placeholder={t('workflow.placeholder_project')}>
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
              name="_templateSelected"
              hasFeedback
              rules={[{ required: true, message: t('workflow.msg_template_required') }]}
            >
              {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
                <NoAvailableTpl>
                  {t(`workflow.msg_${pairingPrefix}no_abailable_tpl`)}
                </NoAvailableTpl>
              ) : (
                <Select
                  loading={tplListQuery.isLoading}
                  disabled={Boolean(tplListQuery.error) || noAvailableTpl}
                  onChange={onTemplateSelectChange}
                  placeholder={t('workflow.placeholder_template')}
                  allowClear
                >
                  {tplList?.map((tpl) => (
                    <Select.Option key={tpl.id} value={tpl.id}>
                      {tpl.name}
                    </Select.Option>
                  ))}
                </Select>
              )}
            </Form.Item>

            <Form.Item name="forkable" label={t('workflow.label_peer_forkable')}>
              <Radio.Group disabled={isAccept}>
                <Radio.Button value={true}>{t('workflow.label_allow')}</Radio.Button>
                <Radio.Button value={false}>{t('workflow.label_not_allow')}</Radio.Button>
              </Radio.Group>
            </Form.Item>

            {workflowConfig?.is_left && (
              <Form.Item
                name="batch_update_interval"
                label={
                  <FormLabel
                    label={t('workflow.label_enable_batch_update_interval')}
                    tooltip={t('workflow.msg_schduled_run')}
                  />
                }
                rules={[
                  {
                    validator: scheduleIntervalValidator,
                    message: t('workflow.msg_min_10_interval'),
                  },
                ]}
              >
                <ScheduledWorkflowRunning />
              </Form.Item>
            )}
          </Form>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16} top="12">
              <Button type="primary" htmlType="submit" onClick={onNextStepClick}>
                {t('next_step')}
              </Button>

              <Button onClick={backToList}>{t('cancel')}</Button>
            </GridRow>
          </Form.Item>
        </StyledForm>
      </Container>
    </Spin>
  );

  async function goNextStep() {
    onSuccess && onSuccess();

    const nextRoute = isInitiate
      ? '/workflows/initiate/config'
      : `/workflows/accept/config/${params.id}`;
    history.push(nextRoute);
  }
  function backToList() {
    history.push('/workflows');
  }
  function setCurrentUsingTemplate(tpl: WorkflowTemplate<any>) {
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
    setFormData(values);
  }
  async function onTemplateSelectChange(id: number) {
    if (!id) {
      // If user clear select
      return;
    }

    const [res, error] = await to(fetchTemplateById(id));

    if (error) {
      message.error(t('workflow.msg_get_tpl_detail_failed'));
      return;
    }
    if (!res.data) return;
    setCurrentUsingTemplate(res.data);
  }
  async function onNextStepClick() {
    try {
      // Any form invalidation happens will throw error to stop the try block
      await formInstance.validateFields();
      goNextStep();
    } catch {
      /** ignore validation error */
    }
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

export default WorkflowsCreateStepOne;
