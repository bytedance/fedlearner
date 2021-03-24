import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Button, Input, Card, Switch, Spin } from 'antd';
import { useTranslation } from 'react-i18next';
import { useHistory, useParams } from 'react-router-dom';
import { useRecoilState } from 'recoil';
import GridRow from 'components/_base/GridRow';
import FormLabel from 'components/FormLabel';
import { templateForm } from 'stores/template';
import { WorkflowTemplatePayload } from 'typings/workflow';
import { useQuery } from 'react-query';
import { fetchTemplateById } from 'services/workflow';
import { upsertValue, TPL_GLOBAL_NODE_UUID, fillEmptyWidgetSchema } from '../store';
import { giveWeakRandomKey } from 'shared/helpers';
import { omit } from 'lodash';
import { parseComplexDictField } from 'shared/formSchema';

const Container = styled(Card)`
  padding-top: 20px;
  min-height: 100%;
`;
const StyledForm = styled(Form)`
  width: 500px;
  margin: 0 auto;
`;

type Props = {
  isEdit?: boolean;
  isHydrated?: React.MutableRefObject<boolean>;
};

const TemplateStepOneBasic: FC<Props> = ({ isEdit, isHydrated }) => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ id?: string }>();

  const [formInstance] = Form.useForm();
  const [template, setTemplateForm] = useRecoilState(templateForm);

  // DO fetch only when it's edit-mode
  const tplQ = useQuery(['fetchTemplate', params.id], () => fetchTemplateById(params.id!), {
    enabled: isEdit && !isHydrated?.current,
    retry: 1,
    refetchOnWindowFocus: false,
    onSuccess(res) {
      /**
       * Parse the template data from server:
       * 1. basic infos like name, group_alias, is_left... write to recoil all the same
       * 2. each job_definition will be tagged with a uuid,
       *    and replace deps souce job name with corresponding uuid,
       *    then the {uuid, dependencies} will save to recoil and real job def values should go ../store.ts
       */
      const { id, name, comment, is_left, group_alias, config } = parseComplexDictField(res.data);

      upsertValue(TPL_GLOBAL_NODE_UUID, { variables: config.variables.map(fillEmptyWidgetSchema) });

      /**
       * 1. Genrate a Map<uuid, job-name>
       * 2. upsert job definition values to store
       *  - need deal variable codes
       */
      const nameToUuidMap = config.job_definitions.reduce((map, job) => {
        const thisJobUuid = giveWeakRandomKey();
        map[job.name] = thisJobUuid;

        const value = omit(job, 'dependencies');
        value.variables = value.variables.map(fillEmptyWidgetSchema);

        upsertValue(thisJobUuid, value);

        return map;
      }, {} as Record<string, string>);

      const jobNodeSlimRawDataList = config.job_definitions.map((job) => {
        const uuid = nameToUuidMap[job.name];

        return {
          uuid,
          dependencies: job.dependencies.map((dep) => ({ source: nameToUuidMap[dep.source] })),
        };
      });

      setTemplateForm({
        id,
        name,
        comment,
        is_left,
        group_alias,
        config: {
          variables: [],
          job_definitions: jobNodeSlimRawDataList,
        },
      });

      formInstance.setFieldsValue({ name, comment, is_left, group_alias });

      if (isHydrated) {
        isHydrated.current = true;
      }
    },
  });

  return (
    <Container bordered={false}>
      <Spin spinning={!!isEdit && tplQ.isLoading}>
        <StyledForm
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          form={formInstance}
          onFinish={onFinish}
          initialValues={template}
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
      </Spin>
    </Container>
  );

  function backToList() {
    history.push('/workflow-templates');
  }
  function onFormChange(
    _: any,
    values: Pick<WorkflowTemplatePayload, 'comment' | 'group_alias' | 'is_left' | 'name'>,
  ) {
    setTemplateForm({
      ...template,
      ...values,
    });
  }
  function onFinish() {
    history.push(
      isEdit ? `/workflow-templates/edit/jobs/${params.id}` : `/workflow-templates/create/jobs`,
    );
  }
};

export default TemplateStepOneBasic;
