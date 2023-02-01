import React, { useEffect, useMemo } from 'react';
import { generatePath, useHistory } from 'react-router';
import routes from 'views/ModelCenter/routes';
import { ModelJobGroup, ResourceTemplateType, TrainRoleType } from 'typings/modelCenter';
import { AlgorithmProject, EnumAlgorithmProjectType } from 'typings/algorithm';
import { MAX_COMMENT_LENGTH } from 'shared/validator';
import {
  ALGORITHM_TYPE_LABEL_MAPPER,
  isNNAlgorithm,
  isTreeAlgorithm,
  lossTypeOptions,
  nnBaseConfigList,
  trainRoleTypeOptions,
  treeBaseConfigList,
} from 'views/ModelCenter/shared';

import { Form, Input, Space, Button, Spin, Tag, Select, Typography } from '@arco-design/web-react';
import BlockRadio from 'components/_base/BlockRadio';
import ConfigForm, { ItemProps } from 'components/ConfigForm';
import ResourceConfig, { MixedAlgorithmType } from 'components/ResourceConfig';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { useGetCurrentPureDomainName } from 'hooks';
import AlgorithmProjectSelect from '../../CreateCentralization/AlgorithmProjectSelect';
import AlgorithmVersionSelect from '../AlgorithmVersionSelect';
import { useQuery } from 'react-query';
import { fetchDataBatchs } from 'services/dataset';

type Props = {
  isLoading?: boolean;
  modelGroup?: ModelJobGroup;
  jobType: string;
  datasetName?: string;
  isFormValueChanged?: boolean;
  stepOneFormConfigValues?: Record<string, any>;
  onFirstStepSubmit: (formInfo: Record<string, any>) => void;
  onFormValueChange?: (...args: any[]) => void;
  formInitialValues?: Record<string, any>;
  treeAdvancedFormItemList?: ItemProps[];
  nnAdvancedFormItemList: ItemProps[];
  algorithmProjectList?: AlgorithmProject[];
  peerAlgorithmProjectList?: AlgorithmProject[];
  datasetBatchType?: 'day' | 'hour';
};

export default function StepOneCoordinator({
  isLoading,
  modelGroup,
  jobType,
  datasetName,
  isFormValueChanged,
  onFirstStepSubmit,
  onFormValueChange,
  formInitialValues,
  nnAdvancedFormItemList,
  treeAdvancedFormItemList,
  algorithmProjectList,
  peerAlgorithmProjectList,
  datasetBatchType = 'day',
}: Props) {
  const history = useHistory();
  const [formInstance] = Form.useForm();
  const myPureDomainName = useGetCurrentPureDomainName();

  const dataBatchsQuery = useQuery(
    ['fetchDataBatch'],
    () => fetchDataBatchs(modelGroup?.dataset_id!),
    {
      enabled: !!modelGroup?.dataset_id,
    },
  );
  const dataBatchsOptions = useMemo(() => {
    return dataBatchsQuery.data?.data.map((item) => {
      return {
        label: item.name,
        value: item.id,
      };
    });
  }, [dataBatchsQuery.data?.data]);

  useEffect(() => {
    if (!formInitialValues) {
      return;
    }
    formInstance.setFieldsValue(formInitialValues);
  }, [formInitialValues, formInstance]);
  return (
    <Spin loading={isLoading}>
      <Form
        className="form-content"
        form={formInstance}
        scrollToFirstError={true}
        initialValues={formInitialValues}
        onValuesChange={onFormValueChange}
        onSubmit={onNextStepClick}
      >
        <section className="form-section">
          <h3>基本信息</h3>
          <Form.Item label="训练名称">
            <Typography.Text bold={true}>{formInitialValues?.name}</Typography.Text>
          </Form.Item>
          <Form.Item
            field={'comment'}
            label={'描述'}
            rules={[
              {
                maxLength: MAX_COMMENT_LENGTH,
                message: '最多为 200 个字符',
              },
            ]}
          >
            <Input.TextArea placeholder={'最多为 200 个字符'} />
          </Form.Item>
        </section>
        <section className="form-section">
          <h3>训练配置</h3>

          <Form.Item label={'联邦类型'}>
            <Typography.Text bold={true}>
              {ALGORITHM_TYPE_LABEL_MAPPER?.[modelGroup?.algorithm_type!]}
            </Typography.Text>
          </Form.Item>

          {isTreeAlgorithm(modelGroup?.algorithm_type as EnumAlgorithmProjectType) &&
            renderTreeParams()}
          {isNNAlgorithm(modelGroup?.algorithm_type as EnumAlgorithmProjectType) &&
            renderNNParams()}
          {modelGroup?.algorithm_type !== EnumAlgorithmProjectType.NN_HORIZONTAL && (
            <Form.Item
              field={'role'}
              label={'训练角色'}
              rules={[{ required: true, message: '必须选择训练角色' }]}
            >
              <BlockRadio isCenter={true} options={trainRoleTypeOptions} />
            </Form.Item>
          )}

          {jobType !== 'repeat' && (
            <Form.Item label={'数据集'}>
              <Spin loading={false}>
                <Space>
                  <Typography.Text bold={true}>{datasetName || ''}</Typography.Text>
                  <Tag color="arcoblue">结果</Tag>
                </Space>
              </Spin>
            </Form.Item>
          )}
        </section>
        <section className="form-section">
          <h3>我方资源配置</h3>
          <Form.Item
            field={'resource_config'}
            label={'资源模版'}
            rules={[{ required: true, message: '必填项' }]}
          >
            <ResourceConfig
              algorithmType={modelGroup?.algorithm_type as MixedAlgorithmType}
              defaultResourceType={ResourceTemplateType.CUSTOM}
              isIgnoreFirstRender={false}
              localDisabledList={['master.replicas']}
            />
          </Form.Item>
        </section>
        {jobType === 'repeat' && (
          <section className="form-section">
            <h3>定时续训</h3>
            <Form.Item label={'定时'}>
              <Typography.Text bold={true}>
                {datasetBatchType === 'hour' ? '每小时' : '每天'}
              </Typography.Text>
            </Form.Item>
            <Form.Item
              label={'数据集'}
              field="data_batch_id"
              rules={[{ required: true, message: '必填项' }]}
            >
              <Select
                prefix={
                  <Space align="center">
                    <Typography.Text bold={true}>{datasetName || ''}</Typography.Text>
                    <Tag color={datasetBatchType === 'hour' ? 'arcoblue' : 'purple'}>
                      {datasetBatchType === 'hour' ? '小时级' : '天级'}
                    </Tag>
                  </Space>
                }
                placeholder="请选择数据批次"
                options={dataBatchsOptions}
                allowClear={true}
                loading={dataBatchsQuery.isFetching}
              />
            </Form.Item>
          </section>
        )}
        <Space>
          <Button type="primary" htmlType="submit">
            下一步
          </Button>
          <ButtonWithModalConfirm
            isShowConfirmModal={isFormValueChanged}
            onClick={() => {
              history.goBack();
            }}
          >
            取消
          </ButtonWithModalConfirm>
        </Space>
      </Form>
    </Spin>
  );
  function renderTreeParams() {
    return (
      <>
        {
          <Form.Item
            field={'loss_type'}
            label={'损失函数类型'}
            rules={[{ required: true, message: '必须选择损失函数类型' }]}
          >
            <BlockRadio.WithTip options={lossTypeOptions} isOneHalfMode={true} />
          </Form.Item>
        }
        <Form.Item
          field={'tree_config'}
          label={'参数配置'}
          rules={[{ required: true, message: '必须填写参数配置' }]}
        >
          <ConfigForm
            cols={2}
            formItemList={treeBaseConfigList}
            isResetOnFormItemListChange={true}
            collapseFormItemList={treeAdvancedFormItemList}
            formProps={{
              style: {
                marginTop: 7,
              },
            }}
          />
        </Form.Item>
      </>
    );
  }
  function renderNNParams() {
    return (
      <>
        <Form.Item label={'算法'} field={`algorithmProjects.${myPureDomainName}`}>
          <AlgorithmProjectSelect
            algorithmType={[modelGroup?.algorithm_type as EnumAlgorithmProjectType]}
            supportEdit={false}
          />
        </Form.Item>
        <Form.Item
          label={'算法版本'}
          field={`${myPureDomainName}.algorithm`}
          rules={[{ required: true, message: '必填项' }]}
        >
          <AlgorithmVersionSelect
            algorithmProjectList={algorithmProjectList || []}
            peerAlgorithmProjectList={peerAlgorithmProjectList || []}
            algorithmProjectUuid={formInstance.getFieldValue(
              `algorithmProjects.${myPureDomainName}`,
            )}
          />
        </Form.Item>
        <Form.Item
          field={'nn_config'}
          label={'参数配置'}
          rules={[{ required: true, message: '必填项' }]}
        >
          <ConfigForm
            cols={2}
            isResetOnFormItemListChange={true}
            formItemList={nnBaseConfigList}
            collapseFormItemList={nnAdvancedFormItemList}
          />
        </Form.Item>
      </>
    );
  }
  function onNextStepClick() {
    formInstance.validate();
    const coordinatorConfig = formInstance.getFieldsValue();
    onFirstStepSubmit?.({
      role: TrainRoleType.LABEL,
      ...formInitialValues,
      ...coordinatorConfig,
    });
    history.push(
      generatePath(routes.ModelTrainJobCreate, {
        id: modelGroup?.id,
        type: jobType,
        step: 'participant',
      }),
    );
  }
}
