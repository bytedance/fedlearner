import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Button, Input, Card, Switch } from 'antd';
import { useTranslation } from 'react-i18next';
import { useHistory } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import GridRow from 'components/_base/GridRow';
import FormLabel from 'components/FormLabel';
import { templateForm } from 'stores/template';
import { WorkflowTemplatePayload } from 'typings/workflow';

const Container = styled(Card)`
  padding-top: 20px;
  min-height: 100%;
`;
const StyledForm = styled(Form)`
  width: 500px;
  margin: 0 auto;
`;

type Props = {
  onSuccess?: any;
};

// TODO: reuse this component on editting?
const TemplateStepOneBasic: FC<Props> = ({ onSuccess }) => {
  const { t } = useTranslation();
  const history = useHistory();

  const [formInstance] = Form.useForm();

  const [formData, setFormData] = useRecoilState(templateForm);

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
          label={t('workflow.label_new_template_name')}
          rules={[{ required: true, message: t('workflow.msg_tpl_name_required') }]}
        >
          <Input placeholder={t('workflow.placeholder_template_name')} />
        </Form.Item>

        <Form.Item
          name="group_alias"
          label={
            <FormLabel
              label={t('workflow.label_group_alias')}
              tooltip="模版根据该字段进行匹配，启动工作流时双侧必须选择相同 Group 名的两份模版"
            />
          }
          rules={[{ required: true, message: t('workflow.msg_group_required') }]}
        >
          <Input placeholder={t('workflow.msg_group_required')} />
        </Form.Item>

        <Form.Item
          name="is_left"
          label={
            <FormLabel
              label={t('workflow.label_is_left')}
              tooltip="模版分为左模版和右模版，双侧能够成功启动一个工作流的条件是两边必须分别用了左和右模版且匹配的模板"
            />
          }
          valuePropName="checked"
          rules={[{ required: true }]}
        >
          <Switch />
        </Form.Item>

        <Form.Item name="comment" label={t('workflow.label_template_comment')}>
          <Input.TextArea rows={4} placeholder={t('workflow.placeholder_comment')} />
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
    history.push('/workflow-templates');
  }
  function onFormChange(
    _: any,
    values: Pick<WorkflowTemplatePayload, 'comment' | 'group_alias' | 'is_left' | 'name'>,
  ) {
    setFormData({
      ...formData,
      ...values,
    });
  }
  function onFinish() {
    onSuccess && onSuccess();

    history.push(`/workflow-templates/create/jobs`);
  }
};

export default TemplateStepOneBasic;
