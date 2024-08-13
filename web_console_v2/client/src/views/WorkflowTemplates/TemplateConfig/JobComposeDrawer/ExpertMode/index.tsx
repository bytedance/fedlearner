import { Input, Select, Switch, Form } from '@arco-design/web-react';
import YAMLTemplateEditorButton from 'components/YAMLTemplateEditorButton';
import { omit } from 'lodash-es';
import React, { FC } from 'react';
import { isValidJobName } from 'shared/validator';
import { JobType } from 'typings/job';
import VariableList from '../VariableList';
import styled from './index.module.less';

type Props = {
  isGlobal: boolean;
  isCheck?: boolean;
};

const jobTypeOptions = Object.values(omit(JobType, 'UNSPECIFIED'));

const ExpertMode: FC<Props> = ({ isGlobal, isCheck }) => {
  return (
    <>
      {!isGlobal && (
        <section className={styled.form_section} style={{ width: 620 }}>
          <h4 className={styled.section_heading}>基本信息</h4>
          <Form.Item
            field="job_type"
            label="任务类型"
            rules={[{ required: true, message: '请输入 Job 名' }]}
          >
            <Select disabled={isCheck} placeholder="请选择任务类型">
              {jobTypeOptions.map((type) => (
                <Select.Option key={type} value={type}>
                  {type}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            field="name"
            label="Job 名称"
            rules={[
              { required: true, message: '请输入 Job 名' },
              {
                validator(value: any, callback: (error?: string) => void) {
                  if (!isValidJobName(value)) {
                    callback('只支持小写字母，数字开头或结尾，可包含“-”，不超过 24 个字符');
                  }
                },
              },
            ]}
          >
            <Input disabled={isCheck} placeholder="请输入 Job 名" />
          </Form.Item>

          <Form.Item field="is_federated" label="是否联邦" triggerPropName="checked">
            <Switch disabled={isCheck} />
          </Form.Item>

          <Form.Item
            field="yaml_template"
            label="YAML 模板"
            rules={[{ required: true, message: '请加入 YAML 模板' }]}
          >
            <YAMLTemplateEditorButton isCheck={isCheck} />
          </Form.Item>
        </section>
      )}

      <section className={styled.form_section} data-fill-width>
        {!isGlobal && <h4 className={styled.section_heading}>自定义变量</h4>}
        <VariableList isCheck={isCheck} />
      </section>
    </>
  );
};

export default ExpertMode;
