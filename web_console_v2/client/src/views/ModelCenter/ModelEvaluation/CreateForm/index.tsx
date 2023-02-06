import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useMutation, useQueries } from 'react-query';
import { generatePath, useHistory, useParams } from 'react-router';
import {
  Button,
  Form,
  FormItemProps,
  Input,
  Space,
  Select,
  Message,
  Card,
  Spin,
  Typography,
  Checkbox,
  Tooltip,
  Tag,
} from '@arco-design/web-react';
import { IconInfoCircle, IconQuestionCircle } from '@arco-design/web-react/icon';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import ResourceConfig from 'components/ResourceConfig';
import DoubleSelect from 'components/DoubleSelect';

import {
  fetchModelJob_new,
  fetchModelDetail_new,
  fetchPeerModelJobDetail_new,
  updateModelJob,
  createModelJob,
} from 'services/modelCenter';

import routes, { ModelEvaluationCreateParams, ModelEvaluationListParams } from '../../routes';
import { ModelJobType, ResourceTemplateType } from 'typings/modelCenter';
import { ModelJob } from 'typings/modelCenter';
import {
  ALGORITHM_TYPE_LABEL_MAPPER,
  Avatar,
  getConfigInitialValues,
  getConfigInitialValuesByDefinition,
  hydrateModalGlobalConfig,
} from '../../shared';
import { cloneDeep, omit } from 'lodash-es';
import { Dataset, DatasetKindLabel } from 'typings/dataset';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { useRecoilQuery } from 'hooks/recoil';
import {
  nnHorizontalEvalTemplateDetailQuery,
  nnTemplateDetailQuery,
  treeTemplateDetailQuery,
} from 'stores/modelCenter';
import { EnumAlgorithmProjectType, Algorithm } from 'typings/algorithm';
import { WorkflowTemplate } from 'typings/workflow';
import { stringifyComplexDictField } from 'shared/formSchema';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantName,
  useGetCurrentProjectParticipantId,
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
} from 'hooks';
import DatasesetSelect from 'components/NewDatasetSelect';
import { OptionInfo } from '@arco-design/web-react/es/Select/interface';
import { fetchDatasetDetail } from 'services/dataset';

import styles from './index.module.less';
import { fetchAlgorithmByUuid } from 'services/algorithm';
import WhichAlgorithm from 'components/WhichAlgorithm';

const formLayout = {
  labelCol: {
    span: 4,
  },
  wrapperCol: {
    span: 20,
  },
};

enum Fields {
  name = 'name',
  comment = 'comment',
  modelId = 'model_id',
  algorithmType = 'algorithm_type',
  datasetId = 'dataset_id',
  config = 'config',
}

enum ModelJobFields {
  GROUP_KEY = 'model_group_id',
  ITEM_KEY = 'dataset_id',
}

const algorithmTypeOptions = [
  {
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.TREE_VERTICAL],
    value: 'TREE_VERTICAL',
  },
  {
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.NN_VERTICAL],
    value: 'NN_VERTICAL',
  },
  {
    label: ALGORITHM_TYPE_LABEL_MAPPER[EnumAlgorithmProjectType.NN_HORIZONTAL],
    value: 'NN_HORIZONTAL',
  },
];

const MODEL_JOB_TYPE_FIELD = 'model_job_type';
const ALGORITHM_ID_FIELD = 'algorithm_id';
const MODEL_JOB_ID_FIELD = 'eval_model_job_id';
const disabledFieldWhenEdit = [
  Fields.algorithmType,
  Fields.modelId,
  MODEL_JOB_TYPE_FIELD,
  MODEL_JOB_ID_FIELD,
  Fields.name,
];

const formConfig: Record<Fields, Partial<FormItemProps>> = {
  [Fields.name]: {
    label: '名称',
    field: Fields.name,
    rules: [
      {
        match: validNamePattern,
        message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
      },
      { required: true, message: '请输入名称' },
    ],
  },
  [Fields.comment]: {
    label: '描述',
    field: Fields.comment,
    rules: [{ maxLength: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }],
  },
  [Fields.config]: {
    label: '资源模板',
    field: Fields.config,
    rules: [{ required: true }],
  },
  [Fields.algorithmType]: {
    label: '类型',
    field: Fields.algorithmType,
    rules: [{ required: true }],
    initialValue: algorithmTypeOptions[0].value,
  },

  [Fields.modelId]: {
    label: '模型',
    field: Fields.modelId,
    rules: [
      {
        required: true,
        message: '请选择模型',
        validator: (val, cb) => {
          const hasValue = Boolean(
            val?.[ModelJobFields.GROUP_KEY] && val?.[ModelJobFields.ITEM_KEY],
          );
          cb(!hasValue ? '请选择模型' : undefined);
        },
      },
    ],
  },
  [Fields.datasetId]: {
    label: '数据集',
    field: Fields.datasetId,
    rules: [{ required: true, message: '请选择数据集' }],
  },
};

const resourceConfigList = [
  'master_replicas',
  'master_cpu',
  'master_mem',
  'ps_replicas',
  'ps_cpu',
  'ps_mem',
  'worker_replicas',
  'worker_cpu',
  'worker_mem',
];

type Props = {
  job?: ModelJob;
  jobType: ModelJobType;
  createReq: (data: any) => Promise<any>;
  patchReq: (jobId: ID, data: any) => Promise<any>;
};

const CreateForm: React.FC<Props> = ({ job, createReq, patchReq, jobType }) => {
  const history = useHistory();
  const params = useParams<ModelEvaluationCreateParams & ModelEvaluationListParams>();
  const [form] = Form.useForm();
  const projectId = useGetCurrentProjectId();
  const myPureDomainName = useGetCurrentPureDomainName();
  const participantName = useGetCurrentProjectParticipantName();
  const participantList = useGetCurrentProjectParticipantList();
  const participantId = useGetCurrentProjectParticipantId();
  const isEdit = (params.action === 'edit' && params.id != null) || params.role === 'receiver';
  const isReceiver = params.role === 'receiver';
  const [selectedModelJob, setSelectedModelJob] = useState<Record<ModelJobFields, ID>>({
    [ModelJobFields.GROUP_KEY]: 0,
    [ModelJobFields.ITEM_KEY]: params.id,
  });
  const [modelJobIsOldVersion, setModelJobIsOldVersion] = useState<boolean>(false);

  const selectedDatasetRef = useRef<Dataset>({} as Dataset);

  const { data: nnTreeTemplateDetail } = useRecoilQuery(treeTemplateDetailQuery);
  const { data: nnHorizontalEvalTemplateDetail } = useRecoilQuery(
    nnHorizontalEvalTemplateDetailQuery,
  );
  const { data: nnVerticalTemplateDetailQuery } = useRecoilQuery(nnTemplateDetailQuery);

  const relativeModel = useQuery(
    ['model-evaluation-relative-model', job?.model_id],
    () => fetchModelDetail_new(projectId!, job?.model_id!).then((res) => res.data),
    {
      enabled: Boolean(projectId && job?.model_id),
      onSuccess(res) {
        if (!res.group_id) {
          return;
        }
        setSelectedModelJob({
          ...selectedModelJob,
          [ModelJobFields.GROUP_KEY]: res.group_id,
        });
        const modelData = {
          [ModelJobFields.GROUP_KEY]: res.group_id!,
          [ModelJobFields.ITEM_KEY]: res.model_job_id!,
        };
        form.setFieldValue(Fields.modelId, { ...modelData });
      },
    },
  );

  const peerModelJobData = useQuery(
    ['model-evaluation-peer-model-detail', modelJobIsOldVersion],
    () =>
      fetchPeerModelJobDetail_new(projectId!, params.id, participantId!).then((res) => res.data),
    {
      enabled: Boolean(projectId && params.id && isEdit && modelJobIsOldVersion),
    },
  );

  const selectedModelJobDetail = useQuery(
    ['model-evaluation-new-model-detail', selectedModelJob?.[ModelJobFields.ITEM_KEY]],
    async () => {
      const modelId = selectedModelJob?.[ModelJobFields.ITEM_KEY];
      if (!projectId || !modelId) {
        return;
      }
      const jobDetail = await fetchModelJob_new(projectId, modelId);
      return jobDetail.data;
    },
  );

  const createMutation = useMutation((value: any) => createReq(value), {
    onError(err: any) {
      Message.error(err.code === 409 ? '名称已存在' : err.message || err);
    },
    onSuccess() {
      Message.success('创建成功');
      history.replace(
        generatePath(routes.ModelEvaluationList, {
          module: params.module,
        }),
      );
    },
  });

  const patchMutation = useMutation((value: any) => patchReq(params.id, value), {
    onError(err: any) {
      Message.error(err.message || err);
    },
    onSuccess() {
      Message.success('已授权模型评估，任务开始运行');
      history.replace(
        generatePath(routes.ModelEvaluationList, {
          module: params.module,
        }),
      );
    },
  });
  const algorithmDetailQueries = useQueries(
    [...participantList.map((participant) => participant.pure_domain_name), myPureDomainName].map(
      (pureDomain) => {
        return {
          queryKey: [
            'fetch-algorithm-detail',
            projectId,
            selectedModelJobDetail?.data?.global_config?.global_config?.[pureDomain]
              ?.algorithm_uuid!,
            pureDomain,
          ],
          queryFn: async () => {
            const res = await fetchAlgorithmByUuid(
              projectId!,
              selectedModelJobDetail?.data?.global_config?.global_config?.[pureDomain]
                ?.algorithm_uuid!,
            );
            return { [pureDomain]: res.data };
          },

          retry: 2,
          enabled: Boolean(
            projectId &&
              selectedModelJobDetail?.data?.global_config?.global_config?.[pureDomain]
                ?.algorithm_uuid,
          ),
          refetchOnWindowFocus: false,
        };
      },
    ),
  );
  const algorithmDetail = useMemo(() => {
    let algorithmMap: Record<string, Algorithm> = {};
    algorithmDetailQueries.forEach((item) => {
      const algorithmValue = item.data as { [key: string]: Algorithm };
      algorithmMap = {
        ...algorithmMap,
        ...algorithmValue,
      };
    });
    return algorithmMap;
  }, [algorithmDetailQueries]);

  useEffect(() => {
    const data = job;
    if (!data) {
      return;
    }
    job?.dataset_id &&
      fetchDatasetDetail(job.dataset_id).then(
        (detail) => {
          selectedDatasetRef.current = detail.data;
        },
        () => {
          selectedDatasetRef.current.id = job?.dataset_id as ID;
        },
      );

    form.setFieldsValue({
      [Fields.name]: data.name,
      [Fields.comment]: data.comment,
      [Fields.datasetId]: data.dataset_id,
      [Fields.algorithmType]: data.algorithm_type,
    });
  }, [job, form]);

  useEffect(() => {
    if (!relativeModel.data) {
      return;
    }

    const selectedModelJob = {
      [ModelJobFields.GROUP_KEY]: relativeModel.data?.group_id!,
      [ModelJobFields.ITEM_KEY]: relativeModel.data?.model_job_id!,
    };
    setSelectedModelJob(selectedModelJob);
    form.setFieldValue(Fields.modelId, { ...selectedModelJob });
  }, [relativeModel.data, form]);

  useEffect(() => {
    if (!peerModelJobData.data || !modelJobIsOldVersion) {
      return;
    }
    const resource_config = getConfigInitialValues(
      peerModelJobData.data?.config!,
      resourceConfigList,
    );
    form.setFieldValue(Fields.config, { ...form.getFieldsValue().config, ...resource_config });
  }, [peerModelJobData, form, modelJobIsOldVersion]);

  useEffect(() => {
    if (!job?.global_config?.global_config) {
      return;
    }
    const globalConfig = job.global_config.global_config;
    const myResourceConfig = getConfigInitialValuesByDefinition(
      globalConfig?.[myPureDomainName]?.variables,
      resourceConfigList,
    );
    const participantResourceConfig: Record<string, any> = {};

    participantList.forEach((participant) => {
      participantResourceConfig[participant.pure_domain_name] = getConfigInitialValuesByDefinition(
        globalConfig?.[participant.pure_domain_name]?.variables,
        resourceConfigList,
      );
    });
    form.setFieldValue(Fields.config, { ...form.getFieldsValue().config, ...myResourceConfig });
    form.setFieldValue('resource_config', {
      ...form.getFieldsValue().resource_config,
      ...participantResourceConfig,
    });
  }, [form, job?.global_config?.global_config, myPureDomainName, participantList]);

  useEffect(() => {
    if (isEdit) {
      setModelJobIsOldVersion(!job?.global_config?.global_config);
      return;
    }
    if (!selectedModelJob.dataset_id || selectedModelJobDetail.isFetching) {
      setModelJobIsOldVersion(false);
      return;
    }
    setModelJobIsOldVersion(!selectedModelJobDetail.data?.global_config?.global_config);
  }, [
    isEdit,
    job?.global_config?.global_config,
    selectedModelJob.dataset_id,
    selectedModelJobDetail.data?.global_config?.global_config,
    selectedModelJobDetail.isFetching,
  ]);
  return (
    <>
      {params.role === 'receiver' ? (
        <Card style={{ marginBottom: 20 }} bordered={false}>
          <Space>
            <Avatar />
            <div>
              {!job ? (
                <Spin />
              ) : (
                <p className={styles.title_text_large}>
                  {participantName}
                  {params.module === 'model-evaluation'
                    ? `向您发起「${job.name}」的模型评估授权申请`
                    : `向您发起「${job.name}」的离线预测授权申请`}
                </p>
              )}
              <small className={styles.small_text}>
                <IconInfoCircle style={{ color: 'var(--color-text-3)', fontSize: 14 }} />{' '}
                {`合作方均同意授权时，${
                  params.module === 'model-evaluation' ? '评估' : '预测'
                }任务将自动运行`}
              </small>
            </div>
          </Space>
        </Card>
      ) : null}
      <Card className={styles.page_section_card} bordered={false}>
        <Form
          className={`${styles.form_container} form-content`}
          form={form}
          {...formLayout}
          onSubmit={modelJobIsOldVersion ? submitWrapper : submitWrapper_new}
          disabled={createMutation.isLoading || patchMutation.isLoading}
          onValuesChange={(changedValue: any) => {
            if (changedValue[Fields.modelId] != null) {
              setSelectedModelJob(changedValue[Fields.modelId]);
            }
          }}
        >
          <section className="form-section">
            <h3>基本信息</h3>
            <Form.Item {...formConfig[Fields.name]}>
              {isReceiver ? (
                <Typography.Text bold={true}> {job?.name} </Typography.Text>
              ) : (
                <Input placeholder={'请输入名称'} />
              )}
            </Form.Item>
            <Form.Item {...formConfig[Fields.comment]}>
              <Input.TextArea placeholder={'最多为 200 个字符'} />
            </Form.Item>
          </section>
          <section className="form-section">
            <h3>{params.module === 'model-evaluation' ? '评估配置' : '预测配置'}</h3>
            <Form.Item {...formConfig[Fields.algorithmType]}>
              {isReceiver ? (
                <Typography.Text bold={true}>
                  {
                    ALGORITHM_TYPE_LABEL_MAPPER[
                      job?.algorithm_type || EnumAlgorithmProjectType.TREE_VERTICAL
                    ]
                  }
                </Typography.Text>
              ) : (
                <Select
                  options={algorithmTypeOptions}
                  showSearch={true}
                  onChange={() => {
                    form.setFieldValue(Fields.modelId, {
                      [ModelJobFields.GROUP_KEY]: undefined,
                      [ModelJobFields.ITEM_KEY]: undefined,
                    });
                  }}
                  filterOption={(inputValue, option) =>
                    option.props.children.toLowerCase().indexOf(inputValue.toLowerCase()) >= 0
                  }
                />
              )}
            </Form.Item>
            <Form.Item
              {...formConfig[Fields.modelId]}
              shouldUpdate={shouldModelJobDoubleSelectUpdate}
            >
              {isReceiver ? (
                <Typography.Text bold={true}>{selectedModelJobDetail?.data?.name} </Typography.Text>
              ) : (
                (values: any) => (
                  <DoubleSelect.ModelJobGroupSelect
                    type={values[Fields.algorithmType]}
                    leftField={ModelJobFields.GROUP_KEY}
                    rightField={ModelJobFields.ITEM_KEY}
                    onLeftOptionsEmpty={() => {
                      form.setFields({
                        [Fields.modelId]: {
                          error: {
                            message: '目标模型不存在，请联系合作伙伴重新选择',
                          },
                        },
                      });
                    }}
                    isClearRightValueAfterLeftSelectChange={true}
                  />
                )
              )}
            </Form.Item>
            {selectedModelJob.dataset_id &&
              selectedModelJobDetail?.data?.algorithm_type &&
              selectedModelJobDetail.data.algorithm_type !==
                EnumAlgorithmProjectType.TREE_VERTICAL &&
              !modelJobIsOldVersion && (
                <Form className={'form-content'} labelCol={{ span: 6 }} wrapperCol={{ span: 18 }}>
                  <Form.Item label={'我方算法'} style={{ marginBottom: 0 }}>
                    <Typography.Text bold={true}>
                      <WhichAlgorithm
                        id={algorithmDetail?.[myPureDomainName]?.id}
                        uuid={algorithmDetail?.[myPureDomainName]?.uuid}
                        participantId={algorithmDetail?.[myPureDomainName]?.participant_id as ID}
                      />
                    </Typography.Text>
                  </Form.Item>
                  {participantList.map((participant) => {
                    return (
                      <Form.Item
                        key={participant.pure_domain_name}
                        label={`「${participant.name}」算法`}
                      >
                        <Typography.Text bold={true}>
                          <WhichAlgorithm
                            id={algorithmDetail?.[participant.pure_domain_name]?.id}
                            uuid={algorithmDetail?.[participant.pure_domain_name]?.uuid}
                            participantId={
                              algorithmDetail?.[participant.pure_domain_name]?.participant_id as ID
                            }
                          />
                        </Typography.Text>
                      </Form.Item>
                    );
                  })}
                </Form>
              )}
            <Form.Item {...formConfig[Fields.datasetId]}>
              {isReceiver && !modelJobIsOldVersion ? (
                <Space>
                  <Typography.Text bold={true}>
                    {selectedDatasetRef.current.name || ''}
                  </Typography.Text>
                  <Tag color="arcoblue">结果</Tag>
                </Space>
              ) : (
                <DatasesetSelect
                  lazyLoad={{
                    page_size: 10,
                    enable: true,
                  }}
                  kind={DatasetKindLabel.PROCESSED}
                  onChange={async (_, option) => {
                    const dataset = (option as OptionInfo)?.extra;
                    selectedDatasetRef.current = dataset;
                  }}
                />
              )}
            </Form.Item>
          </section>
          <section className="form-section">
            <h3>{'资源配置'}</h3>
            <Form.Item
              {...formConfig[Fields.config]}
              shouldUpdate={(pre, cur) => pre[Fields.algorithmType] !== cur[Fields.algorithmType]}
              disabled={isReceiver && !modelJobIsOldVersion}
            >
              {(val: any) => (
                <ResourceConfig
                  key={myPureDomainName}
                  algorithmType={val[Fields.algorithmType]}
                  defaultResourceType={ResourceTemplateType.CUSTOM}
                  isIgnoreFirstRender={false}
                  localDisabledList={['master.replicas']}
                  collapsedOpen={false}
                />
              )}
            </Form.Item>
          </section>
          {!modelJobIsOldVersion &&
            participantList.map((participant) => {
              return (
                <section className="form-section" key={participant.pure_domain_name}>
                  <h3>{`「${participant.name}」资源配置`}</h3>
                  <Form.Item
                    field={`resource_config.${participant.pure_domain_name}`}
                    label="资源配置"
                    rules={[{ required: true }]}
                    shouldUpdate={(pre, cur) =>
                      pre[Fields.algorithmType] !== cur[Fields.algorithmType]
                    }
                    disabled={isReceiver && !modelJobIsOldVersion}
                  >
                    {(val: any) => (
                      <ResourceConfig
                        algorithmType={val[Fields.algorithmType]}
                        defaultResourceType={ResourceTemplateType.CUSTOM}
                        isIgnoreFirstRender={false}
                        localDisabledList={['master.replicas']}
                        collapsedOpen={false}
                      />
                    )}
                  </Form.Item>
                </section>
              );
            })}
          <Space size="large">
            <Button
              className={styles.submit_btn_container}
              onClick={() => form.submit()}
              size="large"
              type="primary"
              loading={createMutation.isLoading || patchMutation.isLoading}
            >
              {params.role === 'receiver'
                ? '确认授权'
                : form.getFieldValue(Fields.algorithmType) !==
                  EnumAlgorithmProjectType.NN_HORIZONTAL
                ? '提交并发送'
                : '提交'}
            </Button>
            <ButtonWithModalConfirm
              disabled={
                createMutation.isLoading ||
                patchMutation.isLoading ||
                !selectedModelJobDetail.isFetched
              }
              isShowConfirmModal={true}
              size="large"
              onClick={() => {
                history.push(
                  generatePath(routes.ModelEvaluationList, {
                    module: params.module,
                  }),
                );
              }}
              title={params.action === 'edit' ? `确认要退出编辑「${job?.name}」？` : '确认要退出？'}
              content={'退出后，当前所填写的信息将被清空。'}
            >
              取消
            </ButtonWithModalConfirm>
            {!modelJobIsOldVersion &&
              form.getFieldValue(Fields.algorithmType) !==
                EnumAlgorithmProjectType.NN_HORIZONTAL && (
                <Form.Item
                  field="metric_is_public"
                  triggerPropName="checked"
                  style={{ marginBottom: 0 }}
                >
                  <Checkbox style={{ width: 200, fontSize: 12 }}>
                    共享模型评估结果
                    <Tooltip content="共享后，合作伙伴能够查看本方评估结果">
                      <IconQuestionCircle />
                    </Tooltip>
                  </Checkbox>
                </Form.Item>
              )}
          </Space>
        </Form>
      </Card>
    </>
  );

  async function submitWrapper(value: any) {
    const algorithmType = selectedModelJobDetail.data?.algorithm_type || job?.algorithm_type;
    const selectedModelJob = selectedModelJobDetail.data;
    const selectedDataset = selectedDatasetRef.current;

    if (!algorithmType || !selectedDataset || !selectedModelJob) {
      return;
    }

    let template: WorkflowTemplate | null = null;

    switch (algorithmType) {
      case EnumAlgorithmProjectType.NN_HORIZONTAL:
        template = nnHorizontalEvalTemplateDetail;
        break;
      case EnumAlgorithmProjectType.NN_VERTICAL:
        template = nnVerticalTemplateDetailQuery;
        break;
      case EnumAlgorithmProjectType.TREE_VERTICAL:
        template = nnTreeTemplateDetail;
        break;
    }

    const payload = {
      ...value,
      [Fields.algorithmType]: algorithmType,
      [MODEL_JOB_TYPE_FIELD]: jobType,
      [ALGORITHM_ID_FIELD]: selectedModelJob?.algorithm_id,
      [MODEL_JOB_ID_FIELD]: selectedModelJob?.id, // handle DoubleSelect value
      config: createPayloadWithWorkflowTemplate(
        value,
        selectedModelJob,
        selectedDataset,
        cloneDeep(template),
      ),
    };

    if (isEdit) {
      patchMutation.mutate(omit(payload, disabledFieldWhenEdit));
      return;
    }
    createMutation.mutate(omit(payload, Fields.modelId));
  }

  async function submitWrapper_new(value: any) {
    if (!projectId) {
      Message.info('请选择工作区！');
      return;
    }
    const algorithmType = selectedModelJobDetail.data?.algorithm_type || job?.algorithm_type;
    const selectedModelJob = selectedModelJobDetail.data;
    const selectedDataset = selectedDatasetRef.current;

    if (!algorithmType || !selectedDataset || !selectedModelJob) {
      return;
    }

    const globalConfig: Record<string, any> = {};
    const coordinatorGlobalConfig = selectedModelJob.global_config?.global_config[myPureDomainName];
    const baseConfig = getConfigInitialValuesByDefinition(
      coordinatorGlobalConfig?.variables!,
      coordinatorGlobalConfig?.variables.map((item) => item.name),
    );
    globalConfig[myPureDomainName] = {
      algorithm_uuid: coordinatorGlobalConfig?.algorithm_uuid,
      algorithm_parameter: coordinatorGlobalConfig?.algorithm_parameter,
      variables: hydrateModalGlobalConfig(coordinatorGlobalConfig?.variables!, {
        ...baseConfig,
        ...value.config,
      }),
    };
    participantList.forEach((participant) => {
      const pureDomainName = participant.pure_domain_name;
      const participantGlobalConfig = selectedModelJob.global_config?.global_config[pureDomainName];
      const participantBaseConfig = getConfigInitialValuesByDefinition(
        participantGlobalConfig?.variables!,
        participantGlobalConfig?.variables.map((item) => item.name),
      );
      globalConfig[pureDomainName] = {
        algorithm_uuid: participantGlobalConfig?.algorithm_uuid,
        algorithm_parameter: participantGlobalConfig?.algorithm_parameter,
        variables: hydrateModalGlobalConfig(participantGlobalConfig?.variables!, {
          ...participantBaseConfig,
          ...value.resource_config[pureDomainName],
        }),
      };
    });
    const payload = {
      name: value.name,
      comment: value.comment,
      dataset_id: value.dataset_id,
      [Fields.algorithmType]: algorithmType,
      [MODEL_JOB_TYPE_FIELD]: jobType,
      [MODEL_JOB_ID_FIELD]: selectedModelJob?.id,
      model_id: selectedModelJob?.output_models[0].id,
      global_config: {
        dataset_uuid: selectedDatasetRef.current?.uuid,
        model_uuid: selectedModelJob?.output_models[0].uuid,
        global_config: globalConfig,
      },
    };

    if (isEdit) {
      try {
        updateModelJob(projectId!, params.id, {
          metric_is_public: value.metric_is_public,
          comment: value.comment,
          auth_status: 'AUTHORIZED',
        });
        Message.success('授权成功！所有合作伙伴授权完成后任务开始运行');
        history.replace(
          generatePath(routes.ModelEvaluationList, {
            module: params.module,
          }),
        );
      } catch (err: any) {
        Message.error(err.message);
      }
      patchMutation.mutate(
        omit(
          { ...payload, metric_is_public: value.metric_is_public },
          disabledFieldWhenEdit.concat(['global_config', 'dataset_id']),
        ),
      );
      return;
    }
    try {
      const res = await createModelJob(projectId!, payload);
      value.metric_is_public && updateModelJob(projectId!, res.data.id, { metric_is_public: true });
      Message.success('创建成功');
      history.replace(
        generatePath(routes.ModelEvaluationList, {
          module: params.module,
        }),
      );
    } catch (err: any) {
      Message.error(err.message);
    }
  }
};

function shouldModelJobDoubleSelectUpdate(prev: any, cur: any) {
  return (
    prev[Fields.algorithmType] !== cur[Fields.algorithmType] ||
    prev[Fields.modelId]?.[ModelJobFields.GROUP_KEY] !==
      cur[Fields.modelId]?.[ModelJobFields.GROUP_KEY] ||
    prev[Fields.modelId]?.[ModelJobFields.ITEM_KEY] !==
      cur[Fields.modelId]?.[ModelJobFields.ITEM_KEY]
  );
}

function createPayloadWithWorkflowTemplate(
  formValue: any,
  relativeJob: ModelJob,
  dataset: Dataset,
  template: WorkflowTemplate | null,
) {
  if (!template) {
    return {};
  }

  const { variables: tplVariables } = template.config.job_definitions[0];
  const { variables: jobVariables } = relativeJob.config.job_definitions[0];
  const varInForm = formValue.config;

  for (let i = 0; i < tplVariables.length; i++) {
    const variable = tplVariables[i];
    const { name } = variable;

    if (varInForm.hasOwnProperty(variable.name)) {
      variable.value = varInForm[variable.name];
    } else {
      if (name === 'data_source' && dataset.data_source) {
        variable.value = dataset.data_source;
      } else if (name === 'data_path' && dataset.path) {
        variable.value = dataset.path;
      } else {
        const jobVariable = jobVariables.find((v) => v.name === name);
        switch (name) {
          case 'mode':
            variable.value = 'eval';
            break;
          case 'load_model_name':
            variable.value = relativeJob.job_name;
            break;
          default:
            if (jobVariable) {
              tplVariables[i] = { ...jobVariable };
            }
            break;
        }
      }
    }
  }

  const processedTypedValueConfig = stringifyComplexDictField(template);
  return processedTypedValueConfig.config;
}

export default CreateForm;
