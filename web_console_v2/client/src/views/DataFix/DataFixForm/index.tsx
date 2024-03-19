import React from 'react';
import SharedPageLayout from 'components/SharedPageLayout';
import { Button, Form, Input, Message, Switch, Select } from '@arco-design/web-react';
import { datasetFix } from 'services/operation';
import { to } from 'shared/helpers';
import { DatasetForceState } from 'typings/dataset';
import { useToggle } from 'react-use';
import './index.less';

const FormItem = Form.Item;

type formData = {
  dataset_id: ID;
  open_force: boolean;
  force: DatasetForceState;
};

const forceOptions = [
  { label: '成功', value: DatasetForceState.SUCCEEDED },
  { label: '运行中', value: DatasetForceState.RUNNING },
  { label: '失败', value: DatasetForceState.FAILED },
];

export default function DataFixForm() {
  const [forceToggle, setForceToggle] = useToggle(false);
  const [formInstance] = Form.useForm<formData>();
  const initFormData = {
    open_force: false,
    force: DatasetForceState.SUCCEEDED,
  };
  return (
    <SharedPageLayout title={'数据集修复'}>
      <div className="data-fix-container">
        <Form className="data-fix-form" initialValues={initFormData} form={formInstance}>
          <FormItem
            label="数据集ID"
            field="dataset_id"
            required
            rules={[
              {
                type: 'string',
                required: true,
                message: '请输入数据集ID',
              },
            ]}
          >
            <Input placeholder="输入需要修复的数据集ID" allowClear />
          </FormItem>
          <FormItem label="强制转换状态" field="open_force">
            <Switch onChange={(val) => setForceToggle(val)} />
          </FormItem>
          {forceToggle && forceSelectRender()}
          <FormItem
            wrapperCol={{
              offset: 10,
            }}
          >
            <Button type="primary" style={{ marginRight: 24 }} onClick={submitForm}>
              {'提交'}
            </Button>
            <Button
              onClick={() => {
                formInstance.resetFields();
              }}
            >
              {'重置'}
            </Button>
          </FormItem>
        </Form>
      </div>
    </SharedPageLayout>
  );

  function forceSelectRender() {
    return (
      <FormItem label="数据集状态" field="force">
        <Select options={forceOptions} />
      </FormItem>
    );
  }

  async function submitForm() {
    const params = formInstance.getFieldsValue();
    const datasetId = params.dataset_id;
    const openForce = params.open_force;
    const force = params.force;
    if (datasetId) {
      const [, err] = await to(
        datasetFix({
          datasetId,
          force: openForce ? force : undefined,
        }),
      );
      if (err) {
        return Message.error(err.message);
      }
      return Message.success('修复成功');
    }
  }
}
