import React, { FC, useEffect, useMemo, useState } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { useQuery } from 'react-query';

import {
  createModelServing_new,
  updateModelServing_new,
  fetchModelServingList_new,
  fetchModelServingDetail_new,
  fetchUserTypeInfo,
} from 'services/modelServing';
import {
  fetchModelList,
  fetchModelJobGroupList,
  fetchModelJobGroupDetail,
} from 'services/modelCenter';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import { convertCpuMToCore } from 'shared/helpers';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { FILTER_SERVING_OPERATOR_MAPPER, cpuIsCpuM, memoryIsMemoryGi } from '../shared';

import { useIsFormValueChange, useGetCurrentProjectId } from 'hooks';

import {
  Spin,
  Form,
  Input,
  Button,
  Message,
  Grid,
  Select,
  Alert,
  Switch,
  Space,
  Typography,
} from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import { FormHeader } from 'components/SharedPageLayout';
import BlockRadio from 'components/_base/BlockRadio';
import InputGroup, { TColumn } from 'components/InputGroup';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import TitleWithIcon from 'components/TitleWithIcon';

import debounce from 'debounce-promise';
import i18n from 'i18n';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { FilterOp } from 'typings/filter';

import styles from './index.module.less';

const { Row, Col } = Grid;

type FormValues = {
  name: string;
  comment: string;
  is_local: boolean;
  model_set: {
    model_set_id: number;
    model_id: number;
  };
  model_id: number;
  resource: [
    {
      cpu: string;
      memory: string;
      replicas: number;
    },
  ];
  instance_num: number;
  auto_update: boolean;
  model_group_id: boolean;
  third_serving: boolean;
  psm: string;
};

const FILTER_MODEL_TRAIN_OPERATOR_MAPPER = {
  role: FilterOp.EQUAL,
  algorithm_type: FilterOp.IN,
  name: FilterOp.CONTAIN,
  configured: FilterOp.EQUAL,
};

const initialValues: any = {
  is_local: false,
  name: undefined,
  comment: undefined,
  model_set: undefined,
  resource: [
    {
      cpu: 1,
      memory: 1,
      replicas: 1,
    },
  ],
  auto_update: false,
  third_serving: false,
  psm: undefined,
};

const getResourceFormColumns = (readonly?: boolean): TColumn[] => [
  {
    type: 'INPUT_NUMBER',
    span: 8,
    dataIndex: 'replicas',
    title: i18n.t('model_serving.label_instance_amount'),
    precision: 0,
    rules: [
      { required: true, message: i18n.t('model_serving.msg_required') },
      { min: 1, type: 'number' },
      { max: 100, type: 'number' },
    ],
    tooltip: i18n.t('tip_replicas_range'),
    mode: 'button',
    min: 1,
    max: 100,
    disabled: readonly,
  },
  {
    type: 'INPUT_NUMBER',
    unitLabel: 'Core',
    span: 8,
    dataIndex: 'cpu',
    title: i18n.t('cpu'),
    precision: 1,
    rules: [{ required: true, message: i18n.t('model_serving.msg_required') }],
    tooltip: i18n.t('tip_please_input_positive_number'),
    placeholder: i18n.t('placeholder_cpu'),
    disabled: readonly,
  },
  {
    type: 'INPUT_NUMBER',
    unitLabel: 'Gi',
    span: 8,
    dataIndex: 'memory',
    title: i18n.t('mem'),
    precision: 0,
    rules: [{ required: true, message: i18n.t('model_serving.msg_required') }],
    tooltip: i18n.t('tip_please_input_positive_integer'),
    placeholder: i18n.t('placeholder_mem'),
    disabled: readonly,
  },
];

const modelGroupIsEmptyRegx = /model\s*in\s*group\s*[0-9]*\s*is\s*not\s*found/i;

const ModelServingForm: FC = () => {
  const history = useHistory();
  const { action, role, id } = useParams<{
    action: string;
    role: string;
    id: string;
  }>();
  const isEdit = action === 'edit';
  const isReceiver = role === 'receiver';

  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [modelChange, setModelChange] = useState(false);
  const [formConfig, setFormConfig] = useState({
    isHorizontalModel: false,
    autoUpdate: false,
    thirdServing: false,
  });

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const projectId = useGetCurrentProjectId();

  const userTypeQuery = useQuery(
    ['fetchUserType', projectId],
    () => fetchUserTypeInfo(projectId!),
    {
      retry: 2,
      enabled: Boolean(projectId),
    },
  );
  const modelServingDetailQuery = useQuery(
    ['fetchModelServingDetail', id],
    () => fetchModelServingDetail_new(projectId!, id),
    {
      cacheTime: 1,
      refetchOnWindowFocus: false,
      enabled: Boolean(id) && Boolean(projectId),
    },
  );

  const modelListQuery = useQuery(
    ['fetchModelList', projectId, formConfig.isHorizontalModel],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchModelList(projectId, {
        algorithm_type: formConfig.isHorizontalModel
          ? EnumAlgorithmProjectType.NN_HORIZONTAL
          : EnumAlgorithmProjectType.NN_VERTICAL,
      });
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelJobGroupListQuery = useQuery(
    ['fetchModelJobGroupList', projectId, formConfig.isHorizontalModel],
    () => {
      if (!projectId) {
        Message.error('请选择工作区');
        return;
      }
      return fetchModelJobGroupList(projectId, {
        filter: filterExpressionGenerator(
          {
            configured: true,
            algorithm_type: formConfig.isHorizontalModel
              ? [EnumAlgorithmProjectType.NN_HORIZONTAL]
              : [EnumAlgorithmProjectType.NN_VERTICAL],
          },
          FILTER_MODEL_TRAIN_OPERATOR_MAPPER,
        ),
      });
    },
    {
      refetchOnWindowFocus: false,
    },
  );

  const userType = useMemo(() => {
    return userTypeQuery.data?.data || [];
  }, [userTypeQuery]);

  const modelServingDetail = useMemo(() => {
    return modelServingDetailQuery.data?.data;
  }, [modelServingDetailQuery]);

  const modelList = useMemo(() => {
    return modelListQuery.data?.data ?? [];
  }, [modelListQuery]);

  const modelJobGroupList = useMemo(() => {
    return modelJobGroupListQuery.data?.data ?? [];
  }, [modelJobGroupListQuery]);

  const payload = useMemo(() => {
    let resultPayload = { target_psm: '-' };
    try {
      resultPayload = JSON.parse(
        modelServingDetail?.remote_platform?.payload ?? JSON.stringify({ target_psm: '-' }),
      );
    } catch (error) {}
    return resultPayload;
  }, [modelServingDetail]);

  const disabled: Partial<Record<keyof FormValues, boolean>> = {
    name: isEdit || isReceiver,
    comment: false,
    is_local: isEdit || isReceiver,
    instance_num: false,
    model_id: isReceiver,
    model_group_id: isReceiver,
    auto_update: isReceiver,
    third_serving: isEdit || isReceiver,
    psm: isEdit || isReceiver,
  };
  const readonlyField: Partial<Record<keyof FormValues, boolean>> = {
    name: isReceiver || isEdit,
    is_local: isReceiver || isEdit,
    model_id:
      isReceiver ||
      (isEdit && !modelServingDetail?.is_local && !modelServingDetail?.remote_platform),
    model_group_id:
      isReceiver ||
      (isEdit && !modelServingDetail?.is_local && !modelServingDetail?.remote_platform),
    auto_update:
      isReceiver ||
      (isEdit && !modelServingDetail?.is_local && !modelServingDetail?.remote_platform),
    psm: isEdit,
    third_serving: isEdit || isReceiver,
  };

  const selectedModelGroupQuery = useQuery(
    ['fetchModelJobGroupDetail', projectId, modelServingDetail?.model_group_id],
    () => fetchModelJobGroupDetail(projectId!, modelServingDetail?.model_group_id!),
    {
      enabled: Boolean(projectId && modelServingDetail?.model_group_id),
      refetchOnWindowFocus: false,
    },
  );

  const selectedModel = useMemo(() => {
    const curModelId = modelServingDetail?.model_id;
    return modelList.find((item) => item.id === curModelId);
  }, [modelList, modelServingDetail?.model_id]);

  const selectedModelGroup = useMemo(() => {
    return selectedModelGroupQuery.data?.data;
  }, [selectedModelGroupQuery.data?.data]);

  const isReceiverModelEmpty = useMemo(() => {
    if (!isReceiver || modelListQuery.isLoading) {
      return false;
    }

    return selectedModel == null;
  }, [isReceiver, modelListQuery.isLoading, selectedModel]);

  const handleOnChangeFederalType = (checked: boolean) => {
    form.setFieldValue('model_id', undefined);
    form.setFieldValue('model_group_id', undefined);
    setFormConfig((prevState) => ({
      ...prevState,
      isHorizontalModel: checked,
    }));
  };

  useEffect(() => {
    let isUnmount = false;
    const data = modelServingDetail;
    if (!data) {
      return;
    }
    setFormConfig({
      isHorizontalModel: data.is_local,
      autoUpdate: Boolean(data.model_group_id),
      thirdServing: Boolean(data.remote_platform),
    });
    form.setFieldsValue({
      name: data.name,
      comment: data.comment,
      is_local: data.is_local,
      model_id: data.model_id,
      model_group_id: data.model_group_id,
      psm: payload.target_psm,
      resource: [
        {
          cpu: cpuIsCpuM(data.resource?.cpu ?? '1')
            ? convertCpuMToCore(data.resource?.cpu, false)
            : data.resource?.cpu,
          memory: memoryIsMemoryGi(data.resource?.memory ?? '1Gi')
            ? data.resource?.memory.slice(0, -2)
            : data.resource?.memory,
          replicas: data.resource?.replicas || 1,
        },
      ],
    });
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      isUnmount = true;
    };
  }, [modelServingDetail, form, payload]);

  return (
    <Spin className={styles.spin_container} loading={modelServingDetailQuery.isLoading}>
      <SharedPageLayout
        title={
          <BackButton
            onClick={() => history.replace('/model-serving')}
            isShowConfirmModal={isFormValueChanged}
          >
            在线服务
          </BackButton>
        }
      >
        {isReceiverModelEmpty ? (
          <div className={styles.empty_model_tip_container}>
            <span>因对应模型不存在，请选择两侧均存在的纵向联邦模型进行部署</span>
          </div>
        ) : (
          <div className={styles.container}>
            <FormHeader>{isEdit ? '编辑服务' : '创建服务'}</FormHeader>
            {isReceiver ? (
              <Alert
                className={styles.styled_info_alert}
                content={'纵向模型服务仅发起方可查看调用地址和 Signature'}
                type="info"
                showIcon
              />
            ) : null}
            <Form
              className={styles.styled_form}
              layout="horizontal"
              initialValues={initialValues}
              form={form}
              labelCol={{ span: 3 }}
              wrapperCol={{ span: 12 }}
              onSubmit={onFinish}
              onSubmitFailed={onFinishFailed}
              onValuesChange={onFormValueChange}
              scrollToFirstError
            >
              <Form.Item
                hasFeedback
                field="name"
                label={'在线服务名称'}
                rules={[
                  { required: true, message: '必填项' },
                  {
                    match: validNamePattern,
                    message:
                      '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
                  },
                  {
                    validator: debounce(async function (value: any, cb) {
                      if (isEdit || isReceiver || !value) {
                        return;
                      }
                      const isDuplicate = await checkNameIsDuplicate(value);
                      cb(isDuplicate ? '在线服务名称已存在' : undefined);
                    }, 300),
                  },
                ]}
              >
                {readonlyField.name ? (
                  <PlainText />
                ) : (
                  <Input placeholder={'请输入在线服务名称'} disabled={disabled.name} allowClear />
                )}
              </Form.Item>
              <Form.Item
                field="comment"
                label={'在线服务描述'}
                rules={[
                  {
                    maxLength: MAX_COMMENT_LENGTH,
                    message: '最多为 200 个字符',
                  },
                ]}
              >
                <Input.TextArea
                  rows={4}
                  name="comment"
                  placeholder={'最多为 200 个字符'}
                  disabled={disabled.comment}
                  showWordLimit
                />
              </Form.Item>
              {Boolean(userType.length) && (
                <Form.Item field="third_serving" label="部署到第三方">
                  {readonlyField.third_serving ? (
                    <Typography.Text bold={true}>
                      {formConfig.thirdServing ? '开启' : '关闭'}
                    </Typography.Text>
                  ) : (
                    <Space>
                      <Switch
                        disabled={disabled.third_serving}
                        onChange={(value) => {
                          setFormConfig((prevState) => ({
                            ...prevState,
                            thirdServing: value,
                          }));
                        }}
                      />
                      <TitleWithIcon
                        title="开启后服务将部署到reckon"
                        isLeftIcon={true}
                        isShowIcon={true}
                        icon={IconInfoCircle}
                      />
                    </Space>
                  )}
                </Form.Item>
              )}
              {formConfig.thirdServing && (
                <Form.Item field="psm" label="psm" rules={[{ required: true }]}>
                  {readonlyField.psm ? (
                    <a href={modelServingDetail?.endpoint} target="_blank" rel="noreferrer">
                      {payload.target_psm}
                    </a>
                  ) : (
                    <Input disabled={disabled.psm} placeholder="请输入psm" />
                  )}
                </Form.Item>
              )}
              <Form.Item
                field="is_local"
                label={'联邦类型'}
                wrapperCol={{ span: 6 }}
                rules={[{ required: true }]}
              >
                {readonlyField.is_local ? (
                  <PlainText valueFormat={(is_local) => (is_local ? '横向联邦' : '纵向联邦')} />
                ) : (
                  <BlockRadio
                    onChange={handleOnChangeFederalType}
                    gap={8}
                    isCenter={true}
                    disabled={disabled.is_local}
                    options={[
                      {
                        label: '纵向联邦',
                        value: false, // note: 先写死，改动 ModelDirectionType 需要动到的地方较多
                      },
                      {
                        label: '横向联邦',
                        value: true,
                      },
                    ]}
                  />
                )}
              </Form.Item>
              <Form.Item field="auto_update" label="自动更新模型" rules={[{ required: true }]}>
                {readonlyField.auto_update ? (
                  <Typography.Text bold={true}>
                    {formConfig.autoUpdate ? '开启' : '关闭'}
                  </Typography.Text>
                ) : (
                  <Space>
                    <Switch
                      disabled={disabled.auto_update}
                      checked={formConfig.autoUpdate}
                      onChange={(value) => {
                        setFormConfig((prevState) => ({
                          ...prevState,
                          autoUpdate: value,
                        }));
                        form.setFieldValue('model_id', undefined);
                        form.setFieldValue('model_group_id', undefined);
                      }}
                    />
                    <TitleWithIcon
                      title="开启后，当所选择的模型训练作业产生新模型时，将自动更新到本服务"
                      isLeftIcon={true}
                      isShowIcon={true}
                      icon={IconInfoCircle}
                    />
                  </Space>
                )}
              </Form.Item>
              {formConfig.autoUpdate ? (
                <Form.Item
                  field="model_group_id"
                  label="模型训练作业"
                  rules={[{ required: true, message: '必填项' }]}
                >
                  {readonlyField.model_group_id ? (
                    <Spin loading={selectedModelGroupQuery.isFetching}>
                      <Typography.Text bold={true}>{selectedModelGroup?.name} </Typography.Text>
                    </Spin>
                  ) : (
                    <Select
                      disabled={disabled.model_group_id}
                      placeholder="请选择模型训练作业"
                      loading={modelJobGroupListQuery.isFetching}
                      showSearch={true}
                      filterOption={(inputValue, option) =>
                        option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                      }
                      options={(modelJobGroupList ?? []).map((item) => ({
                        label: item.name,
                        value: item.id,
                      }))}
                      onChange={(value) => {
                        setModelChange(value !== selectedModelGroup?.id);
                      }}
                    />
                  )}
                </Form.Item>
              ) : (
                <Form.Item
                  field="model_id"
                  label={'模型'}
                  rules={[{ required: true, message: '必填项' }]}
                >
                  {readonlyField.model_id ? (
                    <Typography.Text bold={true}>{selectedModel?.name} </Typography.Text>
                  ) : (
                    <Select
                      disabled={disabled.model_id}
                      placeholder={'请选择模型'}
                      loading={modelListQuery.isFetching}
                      showSearch={true}
                      filterOption={(inputValue, option) =>
                        option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                      }
                      options={(modelListQuery.data?.data ?? []).map((item) => ({
                        label: item.name,
                        value: item.id,
                      }))}
                      onChange={(value) => {
                        setModelChange(value !== selectedModel?.id);
                      }}
                    />
                  )}
                </Form.Item>
              )}

              {!formConfig.thirdServing && (
                <Form.Item label="实例规格" required={true} field="resource">
                  <InputGroup columns={getResourceFormColumns()} disableAddAndDelete={true} />
                </Form.Item>
              )}
              <Row>
                <Col offset={2} span={12}>
                  <div className={styles.button_group}>
                    <Button
                      className={styles.styled_submit_button}
                      type="primary"
                      loading={loading}
                      htmlType="submit"
                    >
                      {!formConfig.isHorizontalModel &&
                      !isReceiver &&
                      !formConfig.thirdServing &&
                      (!isEdit || modelChange)
                        ? '发送至对侧'
                        : '确认'}
                    </Button>
                    <ButtonWithModalConfirm
                      onClick={onCancelClick}
                      isShowConfirmModal={isFormValueChanged}
                    >
                      取消
                    </ButtonWithModalConfirm>
                  </div>
                </Col>
              </Row>
            </Form>
          </div>
        )}
      </SharedPageLayout>
    </Spin>
  );

  function onCancelClick() {
    history.goBack();
  }
  async function onFinish(values: FormValues) {
    if (!projectId) {
      Message.info('请选择工作区');
      return;
    }
    const { name, comment, model_id, model_group_id } = values;
    setLoading(true);
    const { cpu, memory, replicas } = values.resource?.[0] ?? {
      cpu: '1',
      memory: '1',
      replicas: 1,
    };
    const payload_new = { target_psm: values.psm };

    // note: creating service at receiver side is also use the patch method
    if (isEdit || isReceiver) {
      const payload = {
        comment: comment,
        resource: formConfig.thirdServing
          ? undefined
          : {
              cpu: cpu.toString(),
              memory: `${memory}Gi`,
              replicas,
            },
        model_id: modelChange ? model_id : undefined,
        model_group_id: modelChange ? model_group_id : undefined,
      };

      try {
        await updateModelServing_new(projectId, id, payload);
        Message.success(isReceiver ? '创建成功' : '修改成功');
        history.push('/model-serving');
      } catch (error: any) {
        let msg = error.message;
        if (modelGroupIsEmptyRegx.test(msg)) {
          msg = '该模型训练作业暂无训练成功的模型';
        }
        Message.error(msg);
      }
    } else {
      const payload = {
        name: name,
        comment: comment,
        resource: formConfig.thirdServing
          ? undefined
          : {
              cpu: cpu.toString(),
              memory: `${memory}Gi`,
              replicas,
            },
        is_local: formConfig.isHorizontalModel,
        model_id: model_id,
        model_group_id: model_group_id,
        remote_platform: formConfig.thirdServing
          ? {
              platform: userType?.[0].platform,
              payload: JSON.stringify(payload_new),
            }
          : undefined,
      };
      try {
        await createModelServing_new(projectId!, payload);
        Message.success('创建成功');
        history.push('/model-serving');
      } catch (error: any) {
        const { message: errMsg } = error;
        let msg = error.message;

        if (/participant.+code\s*=\s*3/i.test(errMsg)) {
          msg = '合作伙伴侧在线服务名称已存在';
        } else if (/duplicate\s*entry/i.test(msg)) {
          msg = '在线服务名称已存在';
        } else if (modelGroupIsEmptyRegx.test(msg)) {
          msg = '该模型训练作业暂无训练成功的模型';
        }
        Message.error(msg);
      }
    }
    setLoading(false);
  }

  async function checkNameIsDuplicate(name: string) {
    if (!projectId) {
      Message.info('请选择工作区');
      return;
    }
    try {
      const res = await fetchModelServingList_new(projectId!, {
        filter: filterExpressionGenerator(
          {
            name,
          },
          FILTER_SERVING_OPERATOR_MAPPER,
        ),
      });

      return res.data?.length > 0;
    } catch (e) {
      // 如果网络无法请求，就先当没有重名处理
      return false;
    }
  }

  function onFinishFailed() {}
};

type TPlainTextProps = {
  value?: any;
  valueFormat?: (val: any) => string;
};
function PlainText(props: TPlainTextProps) {
  const { value, valueFormat } = props;
  return (
    <Typography.Text bold={true}>
      {typeof valueFormat === 'function' ? valueFormat(value) : value}
    </Typography.Text>
  );
}

export default ModelServingForm;
