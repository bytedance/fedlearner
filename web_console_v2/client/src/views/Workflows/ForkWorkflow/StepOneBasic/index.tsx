import React, { FC } from 'react';
import styled from './index.module.less';
import { Form, Button, Input, Card, Radio } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import { forkWorkflowForm } from 'stores/workflow';
import { useHistory, useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import GridRow from 'components/_base/GridRow';
import { useQuery } from 'react-query';
import { getWorkflowDetailById } from 'services/workflow';
import WhichProject from 'components/WhichProject';
import FormLabel from 'components/FormLabel';
import ScheduledWorkflowRunning, {
  scheduleIntervalValidator,
} from 'views/Workflows/ScheduledWorkflowRunning';
import { validNamePattern, isWorkflowNameUniqWithDebounce } from 'shared/validator';
import { useIsFormValueChange } from 'hooks';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';

type Props = {
  onSuccess: any;
  onFormValueChange?: () => void;
};

const WorkflowForkStepOneBaic: FC<Props> = ({
  onSuccess,
  onFormValueChange: onFormValueChangeFromProps,
}) => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ id: string }>();

  const [formInstance] = Form.useForm();

  const [formData, setFormData] = useRecoilState(forkWorkflowForm);

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    enabled: Boolean(params.id),
    refetchOnWindowFocus: false,
    onSuccess(workflow) {
      const newName = workflow.name + '-copy';

      formInstance.setFieldsValue({
        name: newName,
        forkable: workflow.forkable,
        cron_config: workflow.cron_config,
      });

      setFormData({
        ...formData,
        ...(workflow as any),
        name: newName,
        forked_from: workflow.id,
      });
    },
  });

  const isLocalWorkflow = workflowQuery.data?.is_local;

  return (
    <Card bordered={false} className={styled.container}>
      <Form
        className={styled.styled_form}
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 18 }}
        form={formInstance}
        onSubmit={onFinish}
        onValuesChange={onFormValueChange}
      >
        <Form.Item
          field="name"
          hasFeedback
          label={t('workflow.label_name')}
          rules={[
            { required: true, message: t('workflow.msg_name_required') },
            { max: 255, message: t('workflow.msg_workflow_name_invalid') },
            { match: validNamePattern, message: t('valid_error.name_invalid') },
            {
              validator: isWorkflowNameUniqWithDebounce,
            },
          ]}
        >
          <Input placeholder={t('workflow.placeholder_name')} disabled={workflowQuery.isFetching} />
        </Form.Item>

        <Form.Item label={t('workflow.label_project')}>
          <WhichProject id={workflowQuery.data?.project_id} loading={workflowQuery.isFetching} />
        </Form.Item>

        <Form.Item label={t('workflow.label_template_group')}>
          {workflowQuery.data?.config?.group_alias}
        </Form.Item>

        {!isLocalWorkflow && (
          <Form.Item field="forkable" label={t('workflow.label_peer_forkable')}>
            <Radio.Group type="button">
              <Radio value={true}>{t(`workflow.label_allow`)}</Radio>
              <Radio value={false}>{t(`workflow.label_not_allow`)}</Radio>
            </Radio.Group>
          </Form.Item>
        )}

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

        <Form.Item wrapperCol={{ offset: 6 }}>
          <GridRow gap={16} top="12">
            <Button type="primary" htmlType="submit">
              {t('next_step')}
            </Button>

            <ButtonWithModalConfirm onClick={backToList} isShowConfirmModal={isFormValueChanged}>
              {t('cancel')}
            </ButtonWithModalConfirm>
          </GridRow>
        </Form.Item>
      </Form>
    </Card>
  );

  function backToList() {
    history.push('/workflow-center/workflows');
  }
  function onFormChange(_: any, values: { name: string; cron_config?: string }) {
    onFormValueChangeFromProps?.();
    setFormData({
      ...formData,
      ...values,
    });
  }
  async function getWorkflowDetail() {
    const { data } = await getWorkflowDetailById(params.id);

    return data;
  }
  function onFinish() {
    onSuccess();

    history.push(`/workflow-center/workflows/fork/config/${params.id}`);
  }
};

export default WorkflowForkStepOneBaic;
