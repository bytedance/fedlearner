import React, { forwardRef, ForwardRefRenderFunction, useEffect, useImperativeHandle } from 'react';
import styled from 'styled-components';
import { Drawer, Row, Button, Form, Switch, Input, Select } from 'antd';
import { DrawerProps } from 'antd/lib/drawer';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import GridRow from 'components/_base/GridRow';
import { Close, Swap } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import { JobType, JobDefinitionForm } from 'typings/job';
import { omit } from 'lodash';
import VariableList from './VariableList';
import { DEFAULT_JOB, getOrInsertValueById } from '../../store';
import YAMLTemplateEditorButton from 'components/YAMLTemplateEditorButton';

const Container = styled(Drawer)`
  top: 60px;
  .ant-drawer-body {
    padding-top: 0;
    padding-bottom: 200px;
  }
`;
const DrawerHeader = styled(Row)`
  top: 0;
  margin: 0 -24px 0;
  padding: 20px 16px 20px 24px;
  background-color: white;
  border-bottom: 1px solid var(--lineColor);
`;
const DrawerTitle = styled.h3`
  position: relative;
  margin-bottom: 0;
  margin-right: 10px;
`;
const FormSection = styled.section`
  margin-bottom: 20px;
  padding-top: 24px;
  &:not([data-fill]) {
    padding-right: 60px;
  }
  > h4 {
    margin-bottom: 16px;
    font-size: 15px;
    color: var(--textColorStrong);
  }
`;
const ButtonGridRow = styled(GridRow)`
  position: fixed;
  bottom: 60px;
  width: 100%;
  padding: 20px 0;
  background-color: white;
  border-top: 1px solid var(--lineColor);
`;

interface Props extends DrawerProps {
  isGlobal: boolean;
  uuid?: string;
  onClose?: any;
  onSubmit?: any;
  toggleVisible?: any;
}

export type ExposedRef = {
  validate(): Promise<boolean>;
  getFormValues(): JobDefinitionForm;
  reset(): any;
};

const JobComposerDrawer: ForwardRefRenderFunction<ExposedRef, Props> = (
  { isGlobal, uuid, visible, toggleVisible, onClose, onSubmit, ...props },
  parentRef,
) => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<JobDefinitionForm>();

  useImperativeHandle(parentRef, () => {
    return {
      validate: validateFields,
      getFormValues,
      reset: formInstance.resetFields,
    };
  });

  useEffect(() => {
    if (uuid && formInstance) {
      formInstance.setFieldsValue(getOrInsertValueById(uuid)!);
    }
  }, [uuid, formInstance]);

  return (
    <ErrorBoundary>
      <Container
        getContainer="#app-content"
        visible={visible}
        mask={false}
        width="640px"
        push={{ distance: -240 }}
        onClose={closeDrawer}
        headerStyle={{ display: 'none' }}
        {...props}
      >
        <DrawerHeader align="middle" justify="space-between">
          <Row align="middle">
            <DrawerTitle>编辑 Job</DrawerTitle>
          </Row>
          <GridRow gap="10">
            <Button size="small" icon={<Swap />} disabled>
              切换至简易模式
            </Button>
            <Button size="small" icon={<Close />} onClick={closeDrawer} />
          </GridRow>
        </DrawerHeader>

        <Form
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          form={formInstance}
          onFinish={onFinish}
          initialValues={DEFAULT_JOB}
        >
          {!isGlobal && (
            <FormSection>
              <h4>基本信息</h4>
              <Form.Item
                name="name"
                label={t('workflow.label_job_name')}
                rules={[{ required: true, message: t('workflow.msg_jobname_required') }]}
              >
                <Input placeholder={t('workflow.placeholder_jobname')} />
              </Form.Item>

              <Form.Item
                name="job_type"
                label={t('workflow.label_job_type')}
                rules={[{ required: true, message: t('workflow.msg_jobname_required') }]}
              >
                <Select placeholder={t('workflow.placeholder_job_type')}>
                  {Object.values(omit(JobType, 'UNSPECIFIED')).map((type) => (
                    <Select.Option key={type} value={type}>
                      {type}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="is_federated"
                label={t('workflow.label_job_federated')}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                name="yaml_template"
                label={t('workflow.label_job_yaml')}
                rules={[{ required: true, message: t('workflow.msg_yaml_required') }]}
              >
                <YAMLTemplateEditorButton />
              </Form.Item>
            </FormSection>
          )}

          <FormSection data-fill>
            <h4>自定义变量</h4>
            {/* Form.List inside VariableList */}
            <VariableList form={formInstance} />
          </FormSection>

          <Form.Item wrapperCol={{ offset: 0 }}>
            <ButtonGridRow gap={16} top="12">
              <Button type="primary" htmlType="submit">
                {t('confirm')}
              </Button>

              <Button onClick={closeDrawer}>{t('cancel')}</Button>
            </ButtonGridRow>
          </Form.Item>
        </Form>
      </Container>
    </ErrorBoundary>
  );

  function closeDrawer() {
    onClose && onClose();
    toggleVisible && toggleVisible(false);
  }
  function onFinish(values: JobDefinitionForm) {
    onSubmit && onSubmit(values);
    toggleVisible && toggleVisible(false);
  }
  async function validateFields() {
    try {
      await formInstance.validateFields();
      return true;
    } catch (error) {
      return false;
    }
  }
  function getFormValues() {
    return formInstance.getFieldsValue(true) as JobDefinitionForm;
  }
};

export default forwardRef(JobComposerDrawer);
