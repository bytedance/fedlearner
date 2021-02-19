import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Button, Input, Card } from 'antd';
import { useTranslation } from 'react-i18next';
import { forkWorkflowForm } from 'stores/workflow';
import { useHistory, useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import GridRow from 'components/_base/GridRow';
import { useQuery } from 'react-query';
import { getWorkflowDetailById } from 'services/workflow';
import WhichProject from 'components/WhichProject';

const Container = styled(Card)`
  padding-top: 20px;
  min-height: 100%;
`;
const StyledForm = styled(Form)`
  width: 500px;
  margin: 0 auto;
`;

type Props = {
  onSuccess: any;
};

const WorkflowForkStepOneBaic: FC<Props> = ({ onSuccess }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ id: string }>();

  const [formInstance] = Form.useForm();

  const [formData, setFormData] = useRecoilState(forkWorkflowForm);

  const workflowQuery = useQuery(['getWorkflow', params.id], getWorkflowDetail, {
    enabled: params.id,
    refetchOnWindowFocus: false,
    onSuccess(workflow) {
      const newName = workflow.name + '-duplicated';

      formInstance.setFieldsValue({ name: newName });

      setFormData({
        ...formData,
        ...(workflow as any),
        name: newName,
        forked_from: workflow.id,
      });
    },
  });
  // TODO: if peer workflow unforable, redirect user back !

  return (
    <Container bordered={false}>
      <StyledForm
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 18 }}
        form={formInstance}
        onFinish={onFinish}
        onValuesChange={onFormChange as any}
      >
        <Form.Item
          name="name"
          hasFeedback
          label={t('workflow.label_name')}
          rules={[
            { required: true, message: t('workflow.msg_name_required') },
            // TODO: remove workflow name restriction by using hashed job name
            {
              validator(_, value) {
                if (/^[a-z0-9-]+$/i.test(value)) {
                  return Promise.resolve();
                } else {
                  return Promise.reject(t('workflow.msg_workflow_name_invalid'));
                }
              },
            },
          ]}
        >
          <Input placeholder={t('workflow.placeholder_name')} disabled={workflowQuery.isFetching} />
        </Form.Item>

        <Form.Item label={t('workflow.label_project')}>
          <WhichProject id={workflowQuery.data?.project_id} loading={workflowQuery.isFetching} />
        </Form.Item>

        <Form.Item label={t('workflow.label_peer_forkable')}>
          {workflowQuery.data?.forkable ? '允许' : '不允许'}
        </Form.Item>

        <Form.Item label={t('workflow.label_template_name')}>
          {workflowQuery.data?.config?.group_alias}
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 6 }}>
          <GridRow gap={16} top="12">
            <Button type="primary" htmlType="submit">
              {t('next_step')}
            </Button>

            <Button onClick={backToList}>{t('cancel')}</Button>
          </GridRow>
        </Form.Item>
      </StyledForm>
    </Container>
  );

  function backToList() {
    history.push('/workflows');
  }
  function onFormChange(_: any, values: { name: string }) {
    setFormData({
      ...formData,
      name: values.name,
    });
  }
  async function getWorkflowDetail() {
    const { data } = await getWorkflowDetailById(params.id);

    return data;
  }
  function onFinish() {
    onSuccess();

    history.push(`/workflows/fork/config/${params.id}`);
  }
};

export default WorkflowForkStepOneBaic;
