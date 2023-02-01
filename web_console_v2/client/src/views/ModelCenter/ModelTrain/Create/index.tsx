import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useHistory, useParams } from 'react-router';
import { useQuery } from 'react-query';

import { MAX_COMMENT_LENGTH, validNamePattern } from 'shared/validator';
import {
  checkAlgorithmValueIsEmpty,
  isTreeAlgorithm,
  isNNAlgorithm,
  isVerticalAlgorithm,
  lossTypeOptions,
} from 'views/ModelCenter/shared';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantId,
  useGetCurrentProjectParticipantName,
  useGetCurrentParticipantPureDomainName,
  useGetCurrentPureDomainName,
  useIsFormValueChange,
} from 'hooks';
import { to } from 'shared/helpers';
import {
  createModelJobGroup,
  updateModelJobGroup,
  updatePeerModelJobGroup,
  fetchModelJobGroupDetail,
  fetchPeerModelJobGroupDetail,
  fetchModelJobDefinition,
} from 'services/modelCenter';
import {
  Avatar,
  trainRoleTypeOptions,
  algorithmTypeOptions,
  treeBaseConfigList,
  nnBaseConfigList,
  getAdvanceConfigListByDefinition,
  getTreeBaseConfigInitialValues,
  getTreeAdvanceConfigInitialValues,
  getConfigInitialValues,
  getNNBaseConfigInitialValues,
  getNNAdvanceConfigInitialValues,
  getTreeBaseConfigInitialValuesByDefinition,
  getNNBaseConfigInitialValuesByDefinition,
  hydrateModalGlobalConfig,
} from '../../shared';

import {
  Form,
  Button,
  Input,
  Card,
  Spin,
  Select,
  Message,
  Space,
  Steps,
  Alert,
  Switch,
} from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import BlockRadio from 'components/_base/BlockRadio';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import TitleWithIcon from 'components/TitleWithIcon';
import DatasesetSelect from 'components/NewDatasetSelect';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import ConfigForm from 'components/ConfigForm';
import ResourceConfig, {
  MixedAlgorithmType,
  Value as ResourceConfigValue,
} from 'components/ResourceConfig';
import { LabelStrong } from 'styles/elements';

import routes from '../../routes';

import {
  FederalType,
  LossType,
  ModelJobRole,
  ResourceTemplateType,
  TrainRoleType,
  ModelJobDefinitionResult,
} from 'typings/modelCenter';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { AlgorithmType } from 'typings/modelCenter';
import { Dataset, DatasetKindLabel, DataJobBackEndType } from 'typings/dataset';
import { OptionInfo } from '@arco-design/web-react/es/Select/interface';
import FormLabel from 'components/FormLabel';
import ScheduleTaskSetter, { scheduleTaskValidator } from 'components/ScheduledTaskSetter';
import { useToggle } from 'react-use';
import { fetchDatasetDetail } from 'services/dataset';
import AlgorithmSelect, { AlgorithmSelectValue } from 'components/AlgorithmSelect';

import './index.less';

const Step = Steps.Step;

type TreeConfig = {
  learning_rate: number | string;
  max_iters: number | string;
  max_depth: number | string;
  l2_regularization: number | string;
  max_bins: number | string;
  num_parallel: number | string;
  [key: string]: any;
};
type NNConfig = {
  epoch_num?: number | string;
  verbosity?: number | string;
  sparse_estimator?: string;
  [key: string]: any;
};

export type BaseFormData = {
  name?: string;
  comment?: string;
  federal_type?: FederalType;
  algorithm_type?: AlgorithmType;
  type?: EnumAlgorithmProjectType;
  algorithm?: AlgorithmSelectValue;
  role?: TrainRoleType | null;
  loss_type?: LossType;
  tree_config?: TreeConfig;
  nn_config?: NNConfig;
  dataset_id?: ID;
  resource_config?: ResourceConfigValue;
  cron_config?: string;
  data_source_manual?: boolean;
  custom_data_source?: string;
};
export type FormData = {
  [ModelJobRole.COORDINATOR]: BaseFormData;
  [ModelJobRole.PARTICIPANT]: BaseFormData;
};

const baseInitialFormValues = {
  role: null,
  federal_type: FederalType.VERTICAL,
  algorithm_type: AlgorithmType.TREE,
  type: EnumAlgorithmProjectType.TREE_VERTICAL,
  algorithm: {
    algorithmId: undefined,
    algorithmProjectId: undefined,
    algorithmUuid: undefined,
    config: [],
    path: '',
  },
  loss_type: LossType.LOGISTIC,
  tree_config: {
    learning_rate: 0.3,
    max_iters: 10,
    max_depth: 5,
    l2_regularization: 1,
    max_bins: 33,
    num_parallel: 5,
  },
  nn_config: {
    epoch_num: undefined,
    verbosity: undefined,
    sparse_estimator: undefined,
  },
  cron_config: '',
  data_source_manual: false,
  custom_data_source: '',
};
const initialFormValues: FormData = {
  [ModelJobRole.COORDINATOR]: baseInitialFormValues,
  [ModelJobRole.PARTICIPANT]: baseInitialFormValues,
};

function getFieldKey(field: string, isParticipant = false) {
  return `${isParticipant ? ModelJobRole.PARTICIPANT : ModelJobRole.COORDINATOR}.${field}`;
}

function calcMixedAlgorithmType(federalType: FederalType, algorithmType: AlgorithmType) {
  if (federalType === FederalType.HORIZONTAL) {
    return algorithmType === AlgorithmType.TREE
      ? EnumAlgorithmProjectType.TREE_HORIZONTAL
      : EnumAlgorithmProjectType.NN_HORIZONTAL;
  } else {
    return algorithmType === AlgorithmType.TREE
      ? EnumAlgorithmProjectType.TREE_VERTICAL
      : EnumAlgorithmProjectType.NN_VERTICAL;
  }
}

const Create: React.FC = () => {
  const history = useHistory();
  const { id, action, role } = useParams<{
    role: 'sender' | 'receiver';
    action: 'create' | 'edit';
    id?: string;
  }>();
  const [formInstance] = Form.useForm<FormData>();

  const [datasetId, setDatasetId] = useState<ID>('');
  const [currentStep, setCurrentStep] = useState(1);
  const [dataSourceManual, toggleDataSourceManual] = useToggle(false);
  const [selectedAlgorithmType, setSelectedAlgorithmType] = useState<AlgorithmType>(
    initialFormValues[ModelJobRole.COORDINATOR].algorithm_type || AlgorithmType.TREE,
  );
  const [selectedFederalType, setSelectedFederalType] = useState<FederalType>(
    initialFormValues[ModelJobRole.COORDINATOR].federal_type || FederalType.VERTICAL,
  );
  const [algorithmOwner, setAlgorithmOwner] = useState<string>('');

  const selectedDatasetRef = useRef<Dataset>();

  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const participantName = useGetCurrentProjectParticipantName();
  const myPureDomainName = useGetCurrentPureDomainName();
  const participantPureDomainName = useGetCurrentParticipantPureDomainName();

  const isReceiver = role === 'receiver';
  const isEdit = action === 'edit';

  const currentModelJobGroupQuery = useQuery(
    ['fetchModelJobGroupDetail', projectId, id],
    () => fetchModelJobGroupDetail(projectId!, id!),
    {
      enabled: (isEdit || (isReceiver && !isEdit)) && Boolean(projectId && id),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        if (isReceiver && !isEdit) {
          // get default dataset for coordinator
          setDatasetId(res.data.dataset_id || res.data.intersection_dataset_id);
        }

        if (!isEdit) return;

        const currentModelJobGroupData = res.data;

        let algorithmType = AlgorithmType.TREE;
        const federalType = isVerticalAlgorithm(
          currentModelJobGroupData.algorithm_type as EnumAlgorithmProjectType,
        )
          ? FederalType.VERTICAL
          : FederalType.HORIZONTAL;
        let treeConfig = {} as any;
        let nnConfig = {};
        let topLevelConfig: Record<any, any> = {};

        if (isTreeAlgorithm(currentModelJobGroupData.algorithm_type as EnumAlgorithmProjectType)) {
          algorithmType = AlgorithmType.TREE;

          const baseConfigInitialValues = getTreeBaseConfigInitialValues(
            currentModelJobGroupData.config!,
          );
          const advanceConfigInitialValues = getTreeAdvanceConfigInitialValues(
            currentModelJobGroupData.config!,
          );

          treeConfig = {
            ...baseConfigInitialValues,
            ...advanceConfigInitialValues,
          };

          const topLevelInitialValues = getConfigInitialValues(currentModelJobGroupData.config!, [
            'role',
            'loss_type',
          ]);

          topLevelConfig = topLevelInitialValues;
        } else {
          algorithmType = AlgorithmType.NN;
          const baseConfigInitialValues = getNNBaseConfigInitialValues(
            currentModelJobGroupData.config!,
          );
          const advanceConfigInitialValues = getNNAdvanceConfigInitialValues(
            currentModelJobGroupData.config!,
          );

          nnConfig = {
            ...baseConfigInitialValues,
            ...advanceConfigInitialValues,
          };

          const topLevelInitialValues = getConfigInitialValues(currentModelJobGroupData.config!, [
            'role',
            'algorithm',
          ]);

          topLevelConfig = {
            ...topLevelInitialValues,
            algorithm:
              isEdit && topLevelInitialValues.algorithm
                ? JSON.parse(topLevelInitialValues.algorithm)
                : {},
          };
          setAlgorithmOwner(
            topLevelConfig?.algorithm?.algorithmId === null ||
              topLevelConfig?.algorithm?.algorithmId === 0
              ? 'peer'
              : 'self',
          );
        }
        setSelectedAlgorithmType(algorithmType);
        setSelectedFederalType(federalType);
        toggleDataSourceManual(
          !currentModelJobGroupData.dataset_id && currentModelJobGroupData.dataset_id !== 0,
        );
        formInstance.setFieldsValue({
          [ModelJobRole.COORDINATOR]: {
            name: currentModelJobGroupData.name,
            comment: currentModelJobGroupData.comment ?? '',
            dataset_id:
              currentModelJobGroupData.dataset_id ||
              currentModelJobGroupData.intersection_dataset_id,
            federal_type: federalType,
            algorithm_type: algorithmType,
            type: calcMixedAlgorithmType(federalType, algorithmType),
            tree_config: treeConfig,
            nn_config: nnConfig,
            ...topLevelConfig,
            resource_config: getConfigInitialValues(currentModelJobGroupData.config!, [
              'master_replicas',
              'master_cpu',
              'master_mem',
              'ps_replicas',
              'ps_cpu',
              'ps_mem',
              'worker_replicas',
              'worker_cpu',
              'worker_mem',
            ]),
            cron_config: currentModelJobGroupData.cron_config,
            data_source_manual: !currentModelJobGroupData.dataset_id,
            custom_data_source: treeConfig.data_source ?? '',
          },
        });
      },
    },
  );
  const peerModelJobGroupQuery = useQuery(
    ['fetchPeerModelJobGroupDetail', projectId, id, participantId],
    () => fetchPeerModelJobGroupDetail(projectId!, id!, participantId!),
    {
      enabled:
        currentModelJobGroupQuery.isSuccess &&
        Boolean(projectId && id && participantId) &&
        ((isReceiver && !isEdit) || (!isReceiver && isEdit)),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess: async (res) => {
        const peerModelJobGroupData = res.data;

        const isPeerAuthorized = peerModelJobGroupData?.authorized ?? false;

        // If peer is not authorized, then we should not set peer form value.
        if (!isReceiver && isEdit && !isPeerAuthorized) {
          return;
        }

        let algorithmType = AlgorithmType.TREE;
        const federalType = isVerticalAlgorithm(
          peerModelJobGroupData.algorithm_type as EnumAlgorithmProjectType,
        )
          ? FederalType.VERTICAL
          : FederalType.HORIZONTAL;
        let treeConfig = {};
        let nnConfig = {};
        let topLevelConfig = {};

        if (isTreeAlgorithm(peerModelJobGroupData.algorithm_type as EnumAlgorithmProjectType)) {
          algorithmType = AlgorithmType.TREE;

          const baseConfigInitialValues = getTreeBaseConfigInitialValues(
            peerModelJobGroupData.config!,
          );
          const advanceConfigInitialValues = getTreeAdvanceConfigInitialValues(
            peerModelJobGroupData.config!,
          );

          treeConfig = {
            ...baseConfigInitialValues,
            ...advanceConfigInitialValues,
          };

          const topLevelInitialValues = getConfigInitialValues(peerModelJobGroupData.config!, [
            'role',
            'loss_type',
          ]);

          topLevelConfig = {
            ...topLevelInitialValues,
            role: isReceiver
              ? topLevelInitialValues.role === TrainRoleType.FEATURE
                ? TrainRoleType.LABEL
                : TrainRoleType.FEATURE
              : topLevelInitialValues.role,
          };
        } else {
          algorithmType = AlgorithmType.NN;

          const baseConfigInitialValues = getNNBaseConfigInitialValues(
            peerModelJobGroupData.config!,
          );
          const advanceConfigInitialValues = getNNAdvanceConfigInitialValues(
            peerModelJobGroupData.config!,
          );

          nnConfig = {
            ...baseConfigInitialValues,
            ...advanceConfigInitialValues,
          };

          // when role = receiver and action = create: replace data_path and data_source
          if (isReceiver && !isEdit && datasetId) {
            const [datasetDetail, error] = await to(fetchDatasetDetail(datasetId));
            if (error) {
              Message.error(error.message);
            } else {
              const dataPath = datasetDetail?.data?.path ?? '';
              const dataSource = datasetDetail?.data?.data_source ?? '';
              treeConfig = {
                ...treeConfig,
                data_path: dataPath,
                data_source: dataSource,
              };
              nnConfig = {
                ...nnConfig,
                data_path: dataPath,
                data_source: dataSource,
              };
            }
          }

          const topLevelInitialValues = getConfigInitialValues(peerModelJobGroupData.config!, [
            'role',
            'algorithm',
          ]);

          topLevelConfig = {
            ...topLevelInitialValues,
            role: isReceiver
              ? topLevelInitialValues.role === TrainRoleType.FEATURE
                ? TrainRoleType.LABEL
                : TrainRoleType.FEATURE
              : topLevelInitialValues.role,
            algorithm:
              isEdit && topLevelInitialValues.algorithm
                ? JSON.parse(topLevelInitialValues.algorithm)
                : {},
          };
        }

        setSelectedAlgorithmType(algorithmType);
        setSelectedFederalType(federalType);

        formInstance.setFieldsValue({
          [isReceiver ? ModelJobRole.COORDINATOR : ModelJobRole.PARTICIPANT]: {
            name: peerModelJobGroupData.name,
            federal_type: federalType,
            algorithm_type: algorithmType,
            type: calcMixedAlgorithmType(federalType, algorithmType),
            tree_config: treeConfig,
            nn_config: nnConfig,
            dataset_id: datasetId,
            ...topLevelConfig,
            resource_config: getConfigInitialValues(peerModelJobGroupData.config!, [
              'master_replicas',
              'master_cpu',
              'master_mem',
              'ps_replicas',
              'ps_cpu',
              'ps_mem',
              'worker_replicas',
              'worker_cpu',
              'worker_mem',
            ]),
          },
        });
      },
    },
  );

  const algorithmProjectType = useMemo<EnumAlgorithmProjectType>(() => {
    return calcMixedAlgorithmType(selectedFederalType, selectedAlgorithmType);
  }, [selectedAlgorithmType, selectedFederalType]);

  const modelJobDefinitionQuery = useQuery(['fetchModelJobDefinition', algorithmProjectType], () =>
    fetchModelJobDefinition({
      model_job_type: 'TRAINING',
      algorithm_type: algorithmProjectType || EnumAlgorithmProjectType.TREE_VERTICAL,
    }),
  );
  const modelJobDefinition = useMemo(() => {
    return modelJobDefinitionQuery?.data?.data;
  }, [modelJobDefinitionQuery]);

  const treeAdvancedFormItemList = useMemo(() => {
    if (isNNAlgorithm(algorithmProjectType)) {
      return [];
    } else return getAdvanceConfigListByDefinition(modelJobDefinition?.variables!);
  }, [algorithmProjectType, modelJobDefinition]);

  const nnAdvancedFormItemList = useMemo(() => {
    if (isTreeAlgorithm(algorithmProjectType)) {
      return [];
    } else return getAdvanceConfigListByDefinition(modelJobDefinition?.variables!, true);
  }, [algorithmProjectType, modelJobDefinition]);

  // Set tree_config/nn_config initialValues when create model job group
  useEffect(() => {
    if (isReceiver || isEdit) {
      return;
    }

    let datasetConfigValues: {
      data_path?: string;
      data_source?: string;
    } = {};

    if (selectedDatasetRef.current) {
      datasetConfigValues = {
        data_path: selectedDatasetRef.current?.path ?? '',
        data_source: selectedDatasetRef.current.data_source ?? '',
      };
    }

    if (isTreeAlgorithm(algorithmProjectType)) {
      if (!treeAdvancedFormItemList) {
        return;
      }

      const baseConfigInitialValues = getTreeBaseConfigInitialValuesByDefinition(
        modelJobDefinition?.variables!,
      );
      const advanceConfigConfigInitialValues = treeAdvancedFormItemList.reduce((acc, cur) => {
        acc[cur.field!] = cur.initialValue;
        return acc;
      }, {} as any);

      formInstance.setFieldsValue({
        [ModelJobRole.COORDINATOR]: {
          ...formInstance.getFieldValue(ModelJobRole.COORDINATOR),
          tree_config: {
            ...baseConfigInitialValues,
            ...advanceConfigConfigInitialValues,
            ...datasetConfigValues,
          },
        },
      });
    } else {
      if (!nnAdvancedFormItemList) {
        return;
      }

      const baseConfigInitialValues = getNNBaseConfigInitialValuesByDefinition(
        modelJobDefinition?.variables!,
      );
      const advanceConfigConfigInitialValues = nnAdvancedFormItemList.reduce((acc, cur) => {
        acc[cur.field!] = cur.initialValue;
        return acc;
      }, {} as any);

      formInstance.setFieldsValue({
        [ModelJobRole.COORDINATOR]: {
          ...formInstance.getFieldValue(ModelJobRole.COORDINATOR),
          nn_config: {
            epoch_num: 1,
            verbosity: 1,
            ...baseConfigInitialValues,
            ...advanceConfigConfigInitialValues,
            ...datasetConfigValues,
          },
        },
      });
    }
  }, [
    isReceiver,
    isEdit,
    formInstance,
    algorithmProjectType,
    treeAdvancedFormItemList,
    modelJobDefinition,
    nnAdvancedFormItemList,
  ]);

  const isLoading =
    modelJobDefinitionQuery.isFetching ||
    peerModelJobGroupQuery.isFetching ||
    currentModelJobGroupQuery.isFetching;

  const isPeerAuthorized = peerModelJobGroupQuery.data?.data?.authorized ?? false;
  const isDisabled = isReceiver || (!isReceiver && isEdit);
  const isShowStep = !isReceiver && isEdit && isPeerAuthorized;
  const isShowCanNotEditPeerConfigAlert = !isReceiver && isEdit && !isPeerAuthorized;

  return (
    <SharedPageLayout
      title={
        <BackButton isShowConfirmModal={isFormValueChanged} onClick={goBackToListPage}>
          模型训练
        </BackButton>
      }
      contentWrapByCard={false}
      centerTitle={isEdit ? '编辑训练' : isReceiver ? '授权模型训练' : '创建训练'}
    >
      <Spin loading={isLoading}>
        <div>{isReceiver ? renderReceiverLayout() : renderSenderLayout()}</div>
      </Spin>
    </SharedPageLayout>
  );

  function renderReceiverLayout() {
    return (
      <>
        {!isEdit && renderBannerCard()}
        {renderContentCard()}
      </>
    );
  }
  function renderSenderLayout() {
    return <>{renderContentCard()}</>;
  }
  function renderBannerCard() {
    const title = `${participantName}向您发起「${
      peerModelJobGroupQuery.data?.data?.name ?? ''
    }」训练授权申请`;
    return (
      <Card className="card" bordered={false} style={{ marginBottom: 20 }}>
        <Space size="medium">
          <Avatar />
          <>
            <LabelStrong fontSize={16}>{title ?? '....'}</LabelStrong>
            <TitleWithIcon
              title={
                '授权后，发起方可以运行模型训练并修改参与方的训练参数，训练指标将对所有参与方可见'
              }
              isLeftIcon={true}
              isShowIcon={true}
              icon={IconInfoCircle}
            />
          </>
        </Space>
      </Card>
    );
  }
  function renderContentCard() {
    return (
      <Card className="card" bordered={false}>
        {isShowStep && (
          <Steps className="steps-content" current={currentStep} size="small">
            <Step title={'本侧配置'} />
            <Step title={'合作伙伴配置'} />
          </Steps>
        )}
        <Form<FormData>
          className="form-content"
          form={formInstance}
          initialValues={initialFormValues}
          onSubmit={onSubmit}
          scrollToFirstError={true}
          onValuesChange={onFormValueChange}
        >
          {isShowCanNotEditPeerConfigAlert && (
            <Alert content={'合作伙伴未授权，不能编辑合作伙伴配置'} style={{ marginBottom: 20 }} />
          )}
          <div style={{ display: isShowStep && currentStep === 2 ? 'none' : 'initial' }}>
            {renderBaseInfoConfig()}
            {renderTrainConfig()}
            {renderResourceConfig()}
          </div>
          <div style={{ display: isShowStep && currentStep === 2 ? 'initial' : 'none' }}>
            {renderTrainConfig(true)}
            {renderResourceConfig(true)}
          </div>
          {renderFooterButton()}
        </Form>
      </Card>
    );
  }

  function renderBaseInfoConfig(isParticipant = false) {
    const isHideRule =
      (isParticipant && currentStep === 1) || (!isParticipant && currentStep === 2);
    return (
      <section className="form-section">
        <h3>基本信息</h3>
        <Form.Item
          field={getFieldKey('name', isParticipant)}
          label={'训练名称'}
          rules={
            isHideRule
              ? []
              : [
                  { required: true, message: '必填项' },
                  {
                    match: validNamePattern,
                    message:
                      '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
                  },
                ]
          }
          disabled={isDisabled}
        >
          <Input placeholder={'请填写'} />
        </Form.Item>
        <Form.Item
          field={getFieldKey('comment', isParticipant)}
          label={'描述'}
          rules={
            isHideRule
              ? []
              : [
                  {
                    maxLength: MAX_COMMENT_LENGTH,
                    message: '最多为 200 个字符',
                  },
                ]
          }
        >
          <Input.TextArea placeholder={'最多为 200 个字符'} />
        </Form.Item>
        <Form.Item
          field={getFieldKey('federal_type', isParticipant)}
          label={'联邦类型'}
          hidden={true}
        >
          <Input />
        </Form.Item>
      </section>
    );
  }
  function renderTrainConfig(isParticipant = false) {
    const isHideRule =
      (isParticipant && currentStep === 1) || (!isParticipant && currentStep === 2);

    return (
      <section className="form-section">
        <h3>训练配置</h3>
        {!isParticipant && (
          <>
            <Form.Item
              field={getFieldKey('type', isParticipant)}
              label={'类型'}
              rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
              disabled={isDisabled}
            >
              <Select
                placeholder={'请选择'}
                options={algorithmTypeOptions}
                onChange={(value) => {
                  const [algorithmType, federalType] = value.split('_');
                  setSelectedAlgorithmType(algorithmType.toLowerCase());
                  setSelectedFederalType(federalType.toLowerCase());
                  resetAlgorithmFormValue(isParticipant);
                  if (federalType.toLowerCase() === FederalType.HORIZONTAL) {
                    resetRoleFormValue(isParticipant);
                  }
                  formInstance.setFieldsValue({
                    [ModelJobRole.COORDINATOR]: {
                      ...formInstance.getFieldValue(ModelJobRole.COORDINATOR),
                      dataset_id: undefined,
                    },
                  });
                }}
              />
            </Form.Item>
            <Form.Item
              field={getFieldKey('algorithm_type', isParticipant)}
              label={'算法类型'}
              hidden={true}
            >
              <Input />
            </Form.Item>
          </>
        )}

        {isTreeAlgorithm(algorithmProjectType) && renderTreeParams(isParticipant)}
        {isNNAlgorithm(algorithmProjectType) && renderNNParams(isParticipant)}
        <Form.Item
          field={getFieldKey('role', isParticipant)}
          label={'训练角色'}
          rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
          disabled={isDisabled}
          hidden={selectedFederalType === FederalType.HORIZONTAL}
        >
          <BlockRadio isCenter={true} options={trainRoleTypeOptions} />
        </Form.Item>
        {!isParticipant && (
          <Form.Item
            field={getFieldKey('data_source_manual', isParticipant)}
            label={'手动输入数据源'}
            disabled={isEdit}
            triggerPropName="checked"
          >
            <Switch onChange={onDataSourceManual} />
          </Form.Item>
        )}
        {!isParticipant && renderDatasetSelectConfig(dataSourceManual, isParticipant, isHideRule)}
        {!isParticipant && !isReceiver && (
          <Form.Item
            field={getFieldKey('cron_config', isParticipant)}
            label={
              <FormLabel
                label={'启用定时重训'}
                tooltip={'启用该功能将间隔性地重跑训练任务，且每次训练都将从最新的可用版本开始'}
              />
            }
            rules={[
              {
                validator: scheduleTaskValidator,
                message: '请选择时间',
                validateTrigger: 'onSubmit',
              },
            ]}
          >
            <ScheduleTaskSetter />
          </Form.Item>
        )}
      </section>
    );
  }

  function renderDatasetSelectConfig(
    dataSourceManual: boolean,
    isParticipant: boolean,
    isHideRule: boolean,
  ) {
    return dataSourceManual ? (
      <Form.Item
        field={getFieldKey('custom_data_source', isParticipant)}
        label={'数据源'}
        rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
        disabled={isEdit}
      >
        <Input
          placeholder={'请输入数据源'}
          onChange={async (val) => {
            const configField =
              selectedAlgorithmType === AlgorithmType.TREE
                ? getFieldKey('tree_config', isParticipant)
                : getFieldKey('nn_config', isParticipant);

            const prevConfig = (formInstance.getFieldValue(configField as any) || {}) as
              | TreeConfig
              | NNConfig;
            formInstance.setFieldsValue({
              [configField]: {
                ...prevConfig,
                data_source: val,
              },
            });
          }}
        />
      </Form.Item>
    ) : (
      <Form.Item
        field={getFieldKey('dataset_id', isParticipant)}
        label={'数据集'}
        rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
        disabled={isEdit}
      >
        <DatasesetSelect
          lazyLoad={{
            page_size: 10,
            enable: true,
          }}
          kind={DatasetKindLabel.PROCESSED}
          //TODO：support filter for vertical
          datasetJobKind={
            selectedFederalType === FederalType.HORIZONTAL
              ? DataJobBackEndType.DATA_ALIGNMENT
              : undefined
          }
          onChange={async (_, option) => {
            const dataset = (option as OptionInfo)?.extra as Dataset;
            const dataPath = dataset?.path ?? '';
            const dataSource = dataset?.data_source ?? '';

            selectedDatasetRef.current = dataset;

            const configField =
              selectedAlgorithmType === AlgorithmType.TREE
                ? getFieldKey('tree_config', isParticipant)
                : getFieldKey('nn_config', isParticipant);

            const prevConfig = (formInstance.getFieldValue(configField as any) || {}) as
              | TreeConfig
              | NNConfig;
            formInstance.setFieldsValue({
              [configField]: {
                ...prevConfig,
                data_path: dataPath,
                data_source: dataSource,
              },
            });
          }}
        />
      </Form.Item>
    );
  }

  function renderResourceConfig(isParticipant = false) {
    const isHideRule =
      (isParticipant && currentStep === 1) || (!isParticipant && currentStep === 2);
    return (
      <section className="form-section">
        <h3>资源配置</h3>
        <Form.Item
          field={getFieldKey('resource_config', isParticipant)}
          label={'资源模板'}
          rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
        >
          <ResourceConfig
            algorithmType={algorithmProjectType as MixedAlgorithmType}
            defaultResourceType={ResourceTemplateType.CUSTOM}
            isIgnoreFirstRender={isReceiver}
            localDisabledList={['master.replicas']}
          />
        </Form.Item>
      </section>
    );
  }
  function renderFooterButton() {
    let submitText = '提交并发送';
    if (isReceiver) {
      if (isEdit) {
        submitText = '保存编辑';
      } else {
        submitText = '确认授权';
      }
    } else {
      if (isEdit) {
        submitText = '保存编辑';
      } else {
        submitText = '提交并发送';
      }
    }
    return (
      <Space>
        {isShowStep && currentStep === 1 && (
          <Button type="primary" onClick={onNextStepClick}>
            下一步
          </Button>
        )}

        {(!isShowStep || (isShowStep && currentStep === 2)) && (
          <Button type="primary" htmlType="submit">
            {submitText}
          </Button>
        )}

        {isShowStep && currentStep === 2 && <Button onClick={onPrevStepClick}>上一步</Button>}

        {(!isShowStep || (isShowStep && currentStep === 1)) && (
          <ButtonWithModalConfirm
            isShowConfirmModal={isFormValueChanged}
            onClick={goBackToListPage}
          >
            取消
          </ButtonWithModalConfirm>
        )}

        {!isReceiver && !isEdit && (
          <TitleWithIcon
            title={'训练报告仅自己可见，如需共享报告，请前往训练详情页开启'}
            isLeftIcon={true}
            isShowIcon={true}
            icon={IconInfoCircle}
          />
        )}
      </Space>
    );
  }

  function renderTreeParams(isParticipant = false) {
    const isHideRule =
      (isParticipant && currentStep === 1) || (!isParticipant && currentStep === 2);
    return (
      <>
        {!isParticipant && (
          <Form.Item
            field={getFieldKey('loss_type', isParticipant)}
            label={'损失函数类型'}
            rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
            disabled={isDisabled}
          >
            <BlockRadio.WithTip options={lossTypeOptions} isOneHalfMode={true} />
          </Form.Item>
        )}
        <Form.Item
          field={getFieldKey('tree_config', isParticipant)}
          label={'参数配置'}
          rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
        >
          <ConfigForm
            cols={2}
            formItemList={treeBaseConfigList}
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
  function renderNNParams(isParticipant = false) {
    const isHideRule =
      (isParticipant && currentStep === 1) || (!isParticipant && currentStep === 2);
    return (
      <>
        <Form.Item
          field={getFieldKey('algorithm', isParticipant)}
          label={isParticipant ? '算法超参数' : '算法'}
          rules={
            isHideRule || isParticipant
              ? []
              : [
                  { required: true, message: '必填项' },
                  {
                    validator: checkAlgorithmValueIsEmpty,
                  },
                ]
          }
        >
          <AlgorithmSelect
            leftDisabled={isEdit}
            algorithmType={[algorithmProjectType]}
            onAlgorithmOwnerChange={(value: any) => setAlgorithmOwner(value)}
            algorithmOwnerType={algorithmOwner}
            isParticipant={isParticipant}
          />
        </Form.Item>

        <Form.Item
          field={getFieldKey('nn_config', isParticipant)}
          label={'参数配置'}
          rules={isHideRule ? [] : [{ required: true, message: '必填项' }]}
        >
          <ConfigForm
            cols={2}
            formItemList={nnBaseConfigList}
            collapseFormItemList={nnAdvancedFormItemList}
          />
        </Form.Item>
      </>
    );
  }

  function resetAlgorithmFormValue(isParticipant = false) {
    const defaultAlgorithmValue = {
      algorithmId: undefined,
      algorithmProjectId: undefined,
      algorithmUuid: undefined,
      config: [],
      path: '',
    };

    const roleField = isParticipant ? ModelJobRole.PARTICIPANT : ModelJobRole.COORDINATOR;

    formInstance.setFieldsValue({
      [roleField]: {
        ...formInstance.getFieldValue(roleField),
        algorithm: defaultAlgorithmValue,
      },
    });
  }
  function resetRoleFormValue(isParticipant = false) {
    const roleField = isParticipant ? ModelJobRole.PARTICIPANT : ModelJobRole.COORDINATOR;
    formInstance.setFieldsValue({
      [roleField]: {
        ...formInstance.getFieldValue(roleField),
        role: TrainRoleType.LABEL,
      },
    });
  }
  function goBackToListPage() {
    history.push(routes.ModelTrainList);
  }
  function onPrevStepClick() {
    setCurrentStep((currentStep) => currentStep - 1);
  }
  function onDataSourceManual(checked: boolean) {
    toggleDataSourceManual(checked);
  }
  async function onNextStepClick() {
    await formInstance.validate();
    setCurrentStep((currentStep) => currentStep + 1);
  }

  function getTemplateDetail() {
    const isTree = selectedAlgorithmType === AlgorithmType.TREE;

    if (!modelJobDefinition) {
      if (isTree) {
        Message.error('找不到训练模型模板（树算法）');
        return;
      } else if (selectedFederalType === FederalType.HORIZONTAL) {
        Message.error('找不到训练模型模板（nn算法）');
        return;
      } else {
        Message.error('找不到训练模型模板（横向nn算法）');
        return;
      }
    }
    return modelJobDefinition;
  }

  function onSubmit(formValues: FormData) {
    if (!projectId) {
      Message.info('请选择工作区');
      return;
    }

    const templateDetail: ModelJobDefinitionResult | undefined = getTemplateDetail();

    if (!templateDetail) {
      return;
    }

    if (isReceiver) {
      if (isEdit) {
        onReceiverEditSubmit(formValues, templateDetail);
      } else {
        onReceiverCreateSubmit(formValues, templateDetail);
      }
    } else {
      if (isEdit) {
        onSenderEditSubmit(formValues, templateDetail);
      } else {
        onSenderCreateSubmit(formValues, templateDetail);
      }
    }
  }
  async function onSenderCreateSubmit(
    formValues: FormData,
    templateDetail: ModelJobDefinitionResult,
  ) {
    const coordinatorFormValues = formValues[ModelJobRole.COORDINATOR];
    const isTree = isTreeAlgorithm(coordinatorFormValues.type!);

    const [res, error] = await to(
      createModelJobGroup(projectId!, {
        name: coordinatorFormValues.name!,
        algorithm_type: algorithmProjectType,
        dataset_id: coordinatorFormValues.dataset_id!,
      }),
    );

    if (error) {
      Message.error(error.message);
      return;
    }

    const { id: modelJobGroupId } = res.data;

    const [, updateError] = await to(
      updateModelJobGroup(projectId!, modelJobGroupId, {
        comment: coordinatorFormValues.comment,
        dataset_id: coordinatorFormValues.dataset_id!,
        cron_config: coordinatorFormValues.cron_config,
        global_config: {
          global_config: {
            [myPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    loss_type: coordinatorFormValues.loss_type,
                    ...coordinatorFormValues.tree_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                }
              : {
                  algorithm_uuid: coordinatorFormValues?.algorithm?.algorithmUuid,
                  //TODO：support param algorithm_project_uuid
                  algorithm_parameter: { variables: coordinatorFormValues?.algorithm?.config },
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    ...coordinatorFormValues.nn_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                },
          },
        },
      }),
    );

    if (updateError) {
      Message.error(updateError.message);
      return;
    }

    Message.success('创建成功，等待合作伙伴授权');
    goBackToListPage();
  }

  async function onSenderEditSubmit(
    formValues: FormData,
    templateDetail: ModelJobDefinitionResult,
  ) {
    const coordinatorFormValues = formValues[ModelJobRole.COORDINATOR];
    const participantFormValues = {
      ...formValues[ModelJobRole.PARTICIPANT],
      loss_type: coordinatorFormValues.loss_type,
    };
    const isTree = isTreeAlgorithm(coordinatorFormValues.type!);

    const [, updateError] = await to(
      updateModelJobGroup(projectId!, id!, {
        comment: coordinatorFormValues.comment,
        dataset_id: coordinatorFormValues.dataset_id!,
        cron_config: coordinatorFormValues.cron_config,
        global_config: {
          global_config: {
            [myPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    loss_type: coordinatorFormValues.loss_type,
                    ...coordinatorFormValues.tree_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                }
              : {
                  algorithm_uuid: coordinatorFormValues?.algorithm?.algorithmUuid,
                  //TODO：support param algorithm_project_uuid
                  algorithm_parameter: { variables: coordinatorFormValues?.algorithm?.config },
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    ...coordinatorFormValues.nn_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                },
          },
        },
      }),
    );

    if (updateError) {
      Message.error(updateError.message);
      return;
    }

    if (isShowCanNotEditPeerConfigAlert) {
      Message.success('保存成功');
      goBackToListPage();
      return;
    }

    if (!peerModelJobGroupQuery.data?.data?.config) {
      Message.error('找不到对侧训练模型模板');
      return;
    }

    const [, updatePeerError] = await to(
      updatePeerModelJobGroup(projectId!, id!, participantId!, {
        global_config: {
          global_config: {
            [participantPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: participantFormValues.role,
                    loss_type: participantFormValues.loss_type,
                    ...participantFormValues.tree_config,
                    ...participantFormValues.resource_config,
                  }),
                }
              : {
                  //TODO：support  algorithm_uuid
                  algorithm_parameter: { variables: participantFormValues?.algorithm?.config },
                  // algorithm_uuid: participantFormValues?.algorithm?.algorithmUuid,
                  variables: hydrateModalGlobalConfig(
                    templateDetail?.variables!,
                    {
                      role: participantFormValues.role,
                      algorithm: participantFormValues.algorithm,
                      ...participantFormValues.nn_config,
                      ...participantFormValues.resource_config,
                    },
                    false,
                  ),
                },
          },
        },
      }),
    );

    if (updatePeerError) {
      Message.error(updatePeerError.message);
      return;
    }

    Message.success('保存成功');
    goBackToListPage();
  }
  async function onReceiverCreateSubmit(
    formValues: FormData,
    templateDetail: ModelJobDefinitionResult,
  ) {
    const coordinatorFormValues = formValues[ModelJobRole.COORDINATOR];

    const isTree = isTreeAlgorithm(coordinatorFormValues.type!);

    const [, updateError] = await to(
      updateModelJobGroup(projectId!, id!, {
        comment: coordinatorFormValues.comment,
        dataset_id: coordinatorFormValues.dataset_id!,
        authorized: true,
        global_config: {
          global_config: {
            [myPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    loss_type: coordinatorFormValues.loss_type,
                    ...coordinatorFormValues.tree_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                }
              : {
                  algorithm_uuid: coordinatorFormValues?.algorithm?.algorithmUuid,
                  algorithm_parameter: { variables: coordinatorFormValues?.algorithm?.config },
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    ...coordinatorFormValues.nn_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                },
          },
        },
      }),
    );

    if (updateError) {
      Message.error(updateError.message);
      return;
    }

    Message.success('授权完成，等待合作伙伴运行');
    goBackToListPage();
  }
  async function onReceiverEditSubmit(
    formValues: FormData,
    templateDetail: ModelJobDefinitionResult,
  ) {
    const coordinatorFormValues = formValues[ModelJobRole.COORDINATOR];

    const isTree = isTreeAlgorithm(coordinatorFormValues.type!);

    const [, updateError] = await to(
      updateModelJobGroup(projectId!, id!, {
        comment: coordinatorFormValues.comment,
        dataset_id: coordinatorFormValues.dataset_id!,
        global_config: {
          global_config: {
            [myPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    loss_type: coordinatorFormValues.loss_type,
                    ...coordinatorFormValues.tree_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                }
              : {
                  algorithm_uuid: coordinatorFormValues?.algorithm?.algorithmUuid,
                  algorithm_parameter: { variables: coordinatorFormValues?.algorithm?.config },
                  variables: hydrateModalGlobalConfig(templateDetail?.variables!, {
                    role: coordinatorFormValues.role,
                    ...coordinatorFormValues.nn_config,
                    ...coordinatorFormValues.resource_config,
                  }),
                },
          },
        },
      }),
    );

    if (updateError) {
      Message.error(updateError.message);
      return;
    }

    Message.success('保存成功');
    goBackToListPage();
  }
};

export default Create;
