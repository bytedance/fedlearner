import React, { FC } from 'react';
import { useHistory } from 'react-router-dom';
import { useRecoilState } from 'recoil';

import { useIsFormValueChange } from 'hooks';
import { projectCreateForm, ProjectCreateForm } from 'stores/project';
import { MAX_COMMENT_LENGTH, validNamePattern } from 'shared/validator';

import { Form, Input, Button, Radio } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import EnvVariablesForm from './EnvVariablesForm';
import ActionRules from '../StepTwoPartner/ActionRules';
import { ProjectFormInitialValues, ProjectTaskType } from 'typings/project';

import styles from './index.module.less';

const radioOptions = [
  {
    value: ProjectTaskType.ALIGN,
    label: 'ID对齐（隐私集合求交，求出共有交集，不泄漏交集之外原始数据）',
  },
  {
    value: ProjectTaskType.HORIZONTAL,
    label: '横向联邦学习（包含特征对齐、横向联邦训练、评估、预测能力）',
  },
  {
    value: ProjectTaskType.VERTICAL,
    label: '纵向联邦学习（包含ID对齐、纵向联邦训练、评估、预测能力）',
  },
  {
    value: ProjectTaskType.TRUSTED,
    label: '可信分析服务（包含可信计算分析能力）',
  },
];

const StepOneConfig: FC<{
  isEdit?: boolean;
  onEditFinish?: (payload: any) => Promise<void>;
  initialValues?: ProjectFormInitialValues;
  isLeftLayout?: boolean;
  onFormValueChange?: () => void;
}> = ({
  isEdit = false,
  onEditFinish,
  initialValues,
  isLeftLayout = false,
  onFormValueChange: onFormValueChangeFromProps,
}) => {
  const [form] = Form.useForm();
  const history = useHistory();
  const [projectForm, setProjectForm] = useRecoilState<ProjectCreateForm>(projectCreateForm);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onValuesChange);

  const defaultValues: any = initialValues?.name
    ? initialValues
    : {
        name: '',
        comment: '',
        variables: [],
      };

  return (
    <div className={styles.container}>
      <Form
        form={form}
        layout="vertical"
        onSubmit={isEdit ? editFinish : goStepTwo}
        initialValues={isEdit ? defaultValues : projectForm}
        onValuesChange={onFormValueChange}
      >
        <div style={{ marginBottom: 30 }}>
          <p className={styles.title}>基本信息</p>
          <Form.Item
            label="工作区名称"
            field="name"
            rules={[
              { required: true, message: '请输入工作区名称' },
              {
                match: validNamePattern,
                message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
              },
            ]}
          >
            <Input disabled={isEdit} placeholder="请输入工作区名称" />
          </Form.Item>
          <Form.Item label="工作区描述" field="comment">
            <Input.TextArea maxLength={MAX_COMMENT_LENGTH} placeholder="请为工作区添加描述" />
          </Form.Item>
          <p className={styles.title}>环境变量</p>
          <EnvVariablesForm formInstance={form} isEdit={isEdit} />
          <p className={styles.title}>能力规格</p>

          {isEdit ? (
            <span>
              {radioOptions.find((item) => item.value === initialValues?.config?.abilities?.[0])
                ?.label || '旧版工作区'}
            </span>
          ) : (
            <Form.Item
              field="config.abilities"
              rules={[{ required: true, message: '请选择能力规格' }]}
              normalize={(value) => [value]}
              formatter={(value) => value?.[0]}
            >
              <Radio.Group>
                {radioOptions.map((item) => (
                  <Radio value={item.value} key={item.value}>
                    {item.label}
                  </Radio>
                ))}
              </Radio.Group>
            </Form.Item>
          )}

          {isEdit && initialValues?.config?.abilities?.[0] && (
            <ActionRules taskType={initialValues?.config?.abilities?.[0] as ProjectTaskType} />
          )}
        </div>

        <Form.Item>
          <GridRow
            className={styles.btn_container}
            gap={10}
            justify={isLeftLayout ? 'start' : 'center'}
          >
            <Button className={styles.btn_content} type="primary" htmlType="submit">
              {isEdit ? '提交' : '下一步'}
            </Button>
            <ButtonWithModalConfirm
              onClick={backToList}
              isShowConfirmModal={isFormValueChanged || Boolean(projectForm.name)}
            >
              取消
            </ButtonWithModalConfirm>
          </GridRow>
        </Form.Item>
      </Form>
    </div>
  );

  function backToList() {
    history.push(`/projects`);
  }
  function goStepTwo(values: any) {
    setProjectForm({
      ...projectForm,
      ...values,
      config: {
        ...projectForm.config,
        ...values.config,
      },
    });

    history.push(`/projects/create/authorize`);
  }
  function editFinish(values: any) {
    const editPayload = { ...values, config: { ...defaultValues.config, ...values.config } };
    onEditFinish?.(editPayload);
  }
  function onValuesChange() {
    onFormValueChangeFromProps?.();
  }
};

export default StepOneConfig;
