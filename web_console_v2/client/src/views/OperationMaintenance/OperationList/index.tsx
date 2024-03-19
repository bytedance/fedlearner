import React, { FC, useMemo, useState } from 'react';
import { Form, Input, Select, Button, Table, Message, Space } from '@arco-design/web-react';
import { Role, JobGroupFetchPayload, JobItem } from 'typings/operation';
import { useQuery } from 'react-query';
import { fetchOperationList } from 'services/operation';
import { fetchProjectList } from 'services/project';
import SharedPageLayout from 'components/SharedPageLayout';
import JobDetailDrawer from './JobDetailDrawer';

import styles from './index.module.less';

const FormItem = Form.Item;

const initialFormValues: Partial<JobGroupFetchPayload> = {
  role: undefined,
  name_prefix: '',
  project_name: undefined,
  e2e_image_url: '',
  fedlearner_image_uri: '',
  platform_endpoint: undefined,
};

function equals(x: any, y: any) {
  const f1 = x instanceof Object;
  const f2 = y instanceof Object;
  if (!f1 || !f2) {
    return x === y;
  }
  if (Object.keys(x).length !== Object.keys(y).length) {
    return false;
  }
  const newX = Object.keys(x);
  for (let p in newX) {
    p = newX[p];
    const a = x[p] instanceof Object;
    const b = y[p] instanceof Object;
    if (a && b) {
      equals(x[p], y[p]);
    } else if (x[p] !== y[p]) {
      return false;
    }
  }
  return true;
}

const OperationList: FC = () => {
  const [formInstance] = Form.useForm<JobGroupFetchPayload>();
  const [formParams, setFormParams] = useState<Partial<JobGroupFetchPayload>>(initialFormValues);
  const [isShowJobDetailDrawer, setIsShowJobDetailDrawer] = useState(false);
  const [jobName, setJobName] = useState('');
  const columns = [
    {
      title: 'K8s Job名称',
      dataIndex: 'job_name',
      key: 'job_name',
    },
    {
      title: '测试类型',
      dataIndex: 'job_type',
      key: 'job_type',
    },
    {
      title: '测试状态',
      key: 'operation',
      render: (col: any, record: JobItem) => {
        return (
          <Space>
            <Button type="text" onClick={() => onCheck(record)}>
              查看
            </Button>
          </Space>
        );
      },
    },
  ];
  const roleOptions = [
    {
      label: Role.COORDINATOR,
      value: Role.COORDINATOR,
    },
    {
      label: Role.PARTICIPANT,
      value: Role.PARTICIPANT,
    },
  ];

  const listQuery = useQuery(
    ['fetchOperationList', formParams],
    () => {
      const flag = equals(formParams, initialFormValues);
      if (flag) return;
      return fetchOperationList(formParams);
    },
    {
      retry: 0,
      cacheTime: 0,
      refetchOnWindowFocus: false,
      onError(e: any) {
        if (e.code === 400 || /already\s*exist/.test(e.message)) {
          Message.error('工作已存在，请更改name_prefix字段');
        } else {
          Message.error(e.message);
        }
      },
    },
  );
  const projectList = useQuery(['fetchProjectList'], () => {
    return fetchProjectList();
  });
  const projectOptions = useMemo(() => {
    if (!projectList.data?.data) return [];
    const tempData: Array<{ label: string; value: string }> = [];
    projectList.data.data.forEach((item) => {
      const temp = {
        label: item.name,
        value: item.name,
      };
      tempData.push(temp);
    });
    return tempData;
  }, [projectList]);

  const list = useMemo(() => {
    if (!listQuery.data?.data) {
      return [];
    }
    const list = listQuery.data.data;
    return list;
  }, [listQuery.data]);

  async function submitForm() {
    const value = formInstance.getFieldsValue();
    const flag = equals(value, formParams);
    try {
      await formInstance.validate();
      if (flag) {
        Message.error('工作已存在，请更改name_prefix字段');
      } else {
        setFormParams(value);
      }
    } catch (e) {
      Message.error('校验不通过');
    }
  }

  function onCheck(record: JobItem) {
    setJobName(record.job_name);
    setIsShowJobDetailDrawer(true);
  }

  return (
    <SharedPageLayout title={'基础功能测试'}>
      <div className={styles.div_container}>
        <div className={styles.form_container}>
          <Form
            initialValues={initialFormValues}
            labelCol={{ span: 10 }}
            wrapperCol={{ span: 14 }}
            form={formInstance}
          >
            <FormItem
              label="role"
              field="role"
              required
              rules={[
                {
                  type: 'string',
                  required: true,
                  message: '请选择role',
                },
              ]}
            >
              <Select placeholder="please select" options={roleOptions} allowClear />
            </FormItem>
            <FormItem
              label="name_prefix"
              field="name_prefix"
              required
              rules={[
                {
                  type: 'string',
                  required: true,
                  min: 5,
                  message: '请输入name_prefix，最少5个字符',
                },
              ]}
            >
              <Input placeholder="please enter name_prefix, minimun 5 characters" />
            </FormItem>
            <FormItem
              label="project_name"
              field="project_name"
              required
              rules={[
                {
                  type: 'string',
                  required: true,
                  message: '请选择project_name',
                },
              ]}
            >
              <Select placeholder="please select" options={projectOptions} allowClear />
            </FormItem>
            <FormItem
              label="e2e_image_uri"
              field="e2e_image_uri"
              required
              rules={[
                {
                  type: 'string',
                  required: true,
                  message: '请输入e2e_image_uri',
                },
              ]}
            >
              <Input placeholder="please enter e2e_image_uri" />
            </FormItem>
            <FormItem
              label="fedlearner_image_uri"
              field="fedlearner_image_uri"
              required
              rules={[
                {
                  type: 'string',
                  required: true,
                  message: '请输入fedlearner_image_uri',
                },
              ]}
            >
              <Input placeholder="please enter fedlearner_image_uri" />
            </FormItem>
            <FormItem label="platform_endpoint" field="platform_endpoint">
              <Input placeholder="please enter platform_endpoint" />
            </FormItem>
          </Form>
          <FormItem
            wrapperCol={{
              offset: 10,
            }}
          >
            <Button type="primary" style={{ marginRight: 24 }} onClick={submitForm}>
              提交
            </Button>
            <Button
              style={{ marginRight: 24 }}
              onClick={() => {
                formInstance.resetFields();
              }}
            >
              重置
            </Button>
          </FormItem>
        </div>
        <div className={styles.table_container}>
          <Table columns={columns} data={list} style={{ height: '400px' }} rowKey="job_name" />
        </div>
        <JobDetailDrawer
          visible={isShowJobDetailDrawer}
          data={jobName}
          onCancel={onJobDetailDrawerClose}
        />
      </div>
    </SharedPageLayout>
  );

  function onJobDetailDrawerClose() {
    setIsShowJobDetailDrawer(false);
  }
};

export default OperationList;
