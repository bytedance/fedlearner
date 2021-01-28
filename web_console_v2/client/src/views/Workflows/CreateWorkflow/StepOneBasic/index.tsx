import React, { FC, useState, useEffect } from 'react';
import styled from 'styled-components';
import { Form, Select, Radio, Button, Input, Spin, Card, notification } from 'antd';
import { useTranslation } from 'react-i18next';
import GridRow from 'components/_base/GridRow';
import CreateTemplateForm from './CreateTemplate';
import { useHistory, useLocation, useParams } from 'react-router-dom';
import { cloneDeep } from 'lodash';
import {
  templateInUsing,
  StepOneForm,
  workflowBasicForm,
  workflowGetters,
  workflowInEditing,
  workflowJobsConfigForm,
  peerConfigInPairing,
} from 'stores/workflow';
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil';
import WORKFLOW_CHANNELS, { workflowPubsub } from '../pubsub';
import { useRecoilQuery } from 'hooks/recoil';
import { Workflow, WorkflowTemplate } from 'typings/workflow';
import { useToggle } from 'react-use';
import { projectListQuery } from 'stores/projects';
import { useQuery } from 'react-query';
import {
  fetchWorkflowTemplateList,
  getPeerWorkflowsConfig,
  getWorkflowDetailById,
} from 'services/workflow';
import { WorkflowCreateProps } from '..';

const FormsContainer = styled.div`
  width: 500px;
  margin: 0 auto;
`;
const Container = styled(Card)`
  margin-top: 20px;
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

  const [formInstance] = Form.useForm<StepOneForm>();
  const [submitting, setSubmitting] = useToggle(false);

  const { data: projectList } = useRecoilQuery(projectListQuery);
  const [formData, setFormData] = useRecoilState(workflowBasicForm);
  const setJobsConfigData = useSetRecoilState(workflowJobsConfigForm);
  const { whetherCreateNewTpl } = useRecoilValue(workflowGetters);
  const setWorkflowTemplate = useSetRecoilState(templateInUsing);
  const setPeerConfig = useSetRecoilState(peerConfigInPairing);

  // Using when Participant accept the initiation
  // it should be null if it's Coordinator side initiate a workflow
  const [workflow, setWorkflow] = useRecoilState(workflowInEditing);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    // Only do workflow fetch if:
    // 1. id existed in url
    // 2. in Acceptance mode
    // 3. workflow on store is null (i.e. user landing here not from workflow list)
    enabled: params.id && isAccept && !Boolean(workflow),
    refetchOnWindowFocus: false,
  });
  const peerWorkflowQuery = useQuery(['getPeerWorkflow', params.id], getPeerWorkflow, {
    enabled: params.id && isAccept,
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
      enabled: isInitiate || (!!peerWorkflowQuery.data && groupAlias),
      refetchOnWindowFocus: false,
    },
  );

  const peerErrorMsg = (peerWorkflowQuery.error as Error)?.message;
  useEffect(() => {
    if (peerErrorMsg) {
      notification.error({
        message: t('workflow.msg_peer_config_failed'),
        description: peerErrorMsg + ' 请稍后重试',
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
        <FormsContainer>
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
              rules={[{ required: true, message: t('workflow.msg_name_required') }]}
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

            <Form.Item name="forkable" label={t('workflow.label_peer_forkable')}>
              <Radio.Group disabled={isAccept}>
                <Radio value={true}>{t('workflow.label_allow')}</Radio>
                <Radio value={false}>{t('workflow.label_not_allow')}</Radio>
              </Radio.Group>
            </Form.Item>

            <Form.Item name="_templateType" label={t('workflow.label_template')}>
              <Radio.Group>
                <Radio.Button value={'existing'}>
                  {t(`workflow.label_${pairingPrefix}exist_template`)}
                </Radio.Button>
                <Radio.Button value={'create'}>
                  {t(`workflow.label_${pairingPrefix}new_template`)}
                </Radio.Button>
              </Radio.Group>
            </Form.Item>

            {/* If choose to use an existing template */}
            {!whetherCreateNewTpl && (
              <Form.Item
                name="_templateSelected"
                wrapperCol={{ offset: 6 }}
                hasFeedback
                rules={[{ required: true, message: t('workflow.msg_template_required') }]}
              >
                {noAvailableTpl && !tplListQuery.isLoading && !tplListQuery.isIdle ? (
                  <span>{t(`workflow.msg_${pairingPrefix}no_abailable_tpl`)}</span>
                ) : (
                  <Select
                    loading={tplListQuery.isLoading}
                    disabled={Boolean(tplListQuery.error) || noAvailableTpl}
                    onChange={onTemplateSelectChange}
                    placeholder={t('workflow.placeholder_template')}
                  >
                    {tplList &&
                      tplList.map((tpl) => (
                        <Select.Option key={tpl.id} value={tpl.id}>
                          {tpl.name}
                        </Select.Option>
                      ))}
                  </Select>
                )}
              </Form.Item>
            )}
          </Form>

          {/* If choose to create a new template */}
          {whetherCreateNewTpl && (
            <CreateTemplateForm
              onSuccess={onTplCreateSuccess}
              onError={onTplCreateError}
              groupAlias={groupAlias}
              allowedIsLeftValue={allowedIsLeftValue}
            />
          )}

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16} top="12">
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
                onClick={onNextStepClick}
              >
                {t('next_step')}
              </Button>

              <Button disabled={submitting} onClick={backToList}>
                {t('cancel')}
              </Button>
            </GridRow>
          </Form.Item>
        </FormsContainer>
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
  function setCurrentUsingTemplate(tpl: WorkflowTemplate) {
    setWorkflowTemplate(tpl);
    // Set empty jobs config data once choose different template
    setJobsConfigData(tpl.config);
  }
  async function getWorkflowDetail() {
    const { data } = await getWorkflowDetailById(params.id);
    setWorkflow(data);
    formInstance.setFieldsValue((data as any) as StepOneForm);
  }
  async function getPeerWorkflow() {
    const res = await getPeerWorkflowsConfig(params.id);

    const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.config)!;

    setPeerConfig(anyPeerWorkflow.config!);
    setGroupAlias(anyPeerWorkflow.config?.group_alias || '');

    return anyPeerWorkflow;
  }
  // --------- Handlers -----------
  function onFormChange(_: any, values: StepOneForm) {
    setFormData(values);
  }
  function onTemplateSelectChange(id: number) {
    const target = tplList?.find((item) => item.id === id);
    if (!target) return;
    setCurrentUsingTemplate(cloneDeep(target));
  }
  function onTplCreateSuccess(res: WorkflowTemplate) {
    setSubmitting(false);
    // After click confirm, once tpl create succeed, go next step
    setCurrentUsingTemplate(res);
    goNextStep();
  }
  function onTplCreateError() {
    setSubmitting(false);
  }
  async function onNextStepClick() {
    try {
      // Any form invalidation happens will throw error to stop the try block
      await formInstance.validateFields();

      if (whetherCreateNewTpl) {
        // If the template is newly create, stop the flow and
        // notify the create-template form to send a creation request
        // then waiting for crearte succeed
        // see the subscription of WORKFLOW_CHANNELS.tpl_create_succeed above
        setSubmitting(true);
        return workflowPubsub.publish(WORKFLOW_CHANNELS.create_new_tpl);
      } else {
        // And if not
        // just go next step
        goNextStep();
      }
    } catch {
      /** ignore validation error */
    }
  }
};

function _getInitialValues(form: StepOneForm, workflow: Workflow, projectId?: number) {
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
