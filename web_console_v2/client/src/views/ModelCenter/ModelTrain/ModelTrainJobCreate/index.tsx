import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useParams, useHistory, Route, generatePath } from 'react-router';
import routes from '../../routes';
import {
  createModelJob,
  fetchModelJobDefinition,
  fetchModelJobGroupDetail,
  updateModelJob,
  fetchAutoUpdateModelJobDetail,
} from 'services/modelCenter';
import { fetchDatasetDetail, fetchDatasetJobDetail } from 'services/dataset';
import { fetchPeerAlgorithmProjectList, fetchProjectList } from 'services/algorithm';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
  useIsFormValueChange,
} from 'hooks';
import { AutoModelJobStatus, EnumModelJobType, LossType, TrainRoleType } from 'typings/modelCenter';
import { Participant } from 'typings/participant';
import SharedPageLayout from 'components/SharedPageLayout';
import { Message, Steps, Grid } from '@arco-design/web-react';
import StepOneCoordinator from './StepOneCoordinator';
import BackButton from 'components/BackButton';
import StepTwoParticipant from './StepTwoParticipant';
import { EnumAlgorithmProjectSource, EnumAlgorithmProjectType } from 'typings/algorithm';
import {
  getAdvanceConfigListByDefinition,
  getConfigInitialValuesByDefinition,
  getNNBaseConfigInitialValuesByDefinition,
  getTreeBaseConfigInitialValuesByDefinition,
  hydrateModalGlobalConfig,
  isNNAlgorithm,
  isTreeAlgorithm,
} from 'views/ModelCenter/shared';

import styles from './index.module.less';

const { Row } = Grid;
const { Step } = Steps;

type TRouteParams = {
  id: string;
  step: keyof typeof CreateSteps;
  type: string;
};
enum CreateSteps {
  coordinator = 1,
  participant = 2,
}

function ModelTrainJobCreate() {
  const history = useHistory();
  const { id: modelGroupId, step: createStep, type: jobType } = useParams<TRouteParams>();
  const [currentStep, setCurrentStep] = useState(CreateSteps[createStep || 'coordinator']);
  const [formConfig, setFormConfig] = useState<Record<string, any>>();
  const [stepTwoFormConfig, setStepTwoFormConfig] = useState<Record<string, any>>();
  const [submitLoading, setSubmitLoading] = useState<boolean>(false);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const projectId = useGetCurrentProjectId();
  const myPureDomainName = useGetCurrentPureDomainName();
  const participantList = useGetCurrentProjectParticipantList();

  const modelGroupDetailQuery = useQuery(
    ['fetchModelGroupDetail', projectId, modelGroupId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区！');
        return;
      }
      return fetchModelJobGroupDetail(projectId, modelGroupId);
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelGroupDetail = useMemo(() => modelGroupDetailQuery.data?.data, [modelGroupDetailQuery]);

  const modelJobDefinitionQuery = useQuery(
    ['fetchModelJobDefinition', modelGroupDetail?.algorithm_type],
    () =>
      fetchModelJobDefinition({
        model_job_type: 'TRAINING',
        algorithm_type: modelGroupDetail?.algorithm_type || EnumAlgorithmProjectType.TREE_VERTICAL,
      }),
    {
      refetchOnWindowFocus: false,
    },
  );

  const datasetDetailQuery = useQuery(
    ['fetchDatasetDetail', modelGroupDetail?.dataset_id],
    () => fetchDatasetDetail(modelGroupDetail?.dataset_id),
    {
      enabled: Boolean(modelGroupDetail?.dataset_id) || modelGroupDetail?.dataset_id === 0,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const datasetJobQuery = useQuery(
    ['fetchDatasetJobDetail', projectId, datasetDetailQuery.data?.data.parent_dataset_job_id],
    () => fetchDatasetJobDetail(projectId!, datasetDetailQuery.data?.data.parent_dataset_job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled:
        Boolean(projectId && datasetDetailQuery.data?.data.parent_dataset_job_id) &&
        jobType === 'repeat',
    },
  );

  const algorithmProjectListQuery = useQuery(
    ['fetchAllAlgorithmProjectList', modelGroupDetail?.algorithm_type, projectId],
    () =>
      fetchProjectList(projectId, {
        type: [modelGroupDetail?.algorithm_type],
      }),
    {
      enabled: Boolean(projectId && modelGroupDetail?.algorithm_type),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const preAlgorithmProjectListQuery = useQuery(
    ['fetchPreAlgorithmProjectListQuery', modelGroupDetail?.algorithm_type],
    () =>
      fetchProjectList(0, {
        type: [modelGroupDetail?.algorithm_type],
        sources: EnumAlgorithmProjectSource.PRESET,
      }),
    {
      enabled: !!modelGroupDetail?.algorithm_type,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const peerAlgorithmProjectListQuery = useQuery(
    ['fetchPeerAlgorithmProjectListQuery', projectId, modelGroupDetail?.algorithm_type],
    () =>
      fetchPeerAlgorithmProjectList(projectId, 0, {
        filter: `(type:${JSON.stringify([modelGroupDetail?.algorithm_type])})`,
      }),
    {
      enabled: Boolean(projectId && modelGroupDetail?.algorithm_type),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelJobDefinition = useMemo(() => {
    return modelJobDefinitionQuery?.data?.data;
  }, [modelJobDefinitionQuery]);

  const treeAdvancedFormItemList = useMemo(() => {
    if (isNNAlgorithm(modelGroupDetail?.algorithm_type as EnumAlgorithmProjectType)) {
      return [];
    } else return getAdvanceConfigListByDefinition(modelJobDefinition?.variables!);
  }, [modelGroupDetail?.algorithm_type, modelJobDefinition]);

  const nnAdvancedFormItemList = useMemo(() => {
    if (isTreeAlgorithm(modelGroupDetail?.algorithm_type as EnumAlgorithmProjectType)) {
      return [];
    } else return getAdvanceConfigListByDefinition(modelJobDefinition?.variables!, true);
  }, [modelGroupDetail?.algorithm_type, modelJobDefinition]);

  const { treeBaseConfigInitialValues, nnBaseConfigInitialValues } = useMemo(() => {
    if (!modelJobDefinition?.variables) {
      return {};
    }
    return {
      treeBaseConfigInitialValues: getTreeBaseConfigInitialValuesByDefinition(
        modelJobDefinition.variables,
      ),
      nnBaseConfigInitialValues: getNNBaseConfigInitialValuesByDefinition(
        modelJobDefinition.variables,
      ),
    };
  }, [modelJobDefinition?.variables]);

  const { treeAdvanceConfigInitialValues, nnAdvanceConfigInitialValues } = useMemo(() => {
    return {
      treeAdvanceConfigInitialValues: treeAdvancedFormItemList.reduce((acc, cur) => {
        acc[cur.field!] = cur.initialValue;
        return acc;
      }, {} as any),
      nnAdvanceConfigInitialValues: nnAdvancedFormItemList.reduce((acc, cur) => {
        acc[cur.field!] = cur.initialValue;
        return acc;
      }, {} as any),
    };
  }, [treeAdvancedFormItemList, nnAdvancedFormItemList]);

  const baseNN = useMemo(() => {
    return {
      epoch_num: 1,
      verbosity: 1,
      ...nnBaseConfigInitialValues,
      ...nnAdvanceConfigInitialValues,
    };
  }, [nnBaseConfigInitialValues, nnAdvanceConfigInitialValues]);
  const baseTree = useMemo(() => {
    return {
      learning_rate: 0.3,
      max_iters: 10,
      max_depth: 5,
      l2_regularization: 1,
      max_bins: 33,
      num_parallel: 5,
      ...treeBaseConfigInitialValues,
      ...treeAdvanceConfigInitialValues,
    };
  }, [treeBaseConfigInitialValues, treeAdvanceConfigInitialValues]);

  const datasetDetail = useMemo(() => datasetDetailQuery.data?.data, [datasetDetailQuery]);
  const datasetJob = useMemo(() => datasetJobQuery.data?.data, [datasetJobQuery]);

  const algorithmProjectList = useMemo(() => {
    return [
      ...(algorithmProjectListQuery?.data?.data || []),
      ...(preAlgorithmProjectListQuery.data?.data || []),
    ];
  }, [algorithmProjectListQuery, preAlgorithmProjectListQuery]);

  const peerAlgorithmProjectList = useMemo(() => {
    return peerAlgorithmProjectListQuery.data?.data || [];
  }, [peerAlgorithmProjectListQuery]);

  const stepOneInitialValues = useMemo(() => {
    return (
      formConfig ?? {
        name: `${modelGroupDetail?.name}-v${modelGroupDetail?.latest_version! + 1}`,
        algorithmProjects: modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects,
        nn_config: baseNN,
        loss_type: LossType.LOGISTIC,
        tree_config: baseTree,
      }
    );
  }, [
    baseNN,
    baseTree,
    formConfig,
    modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects,
    modelGroupDetail?.latest_version,
    modelGroupDetail?.name,
  ]);
  const stepTwoInitialValues = useMemo(() => {
    if (stepTwoFormConfig) {
      return stepTwoFormConfig;
    }
    const participantConfigInitialValues: Record<string, any> = {};
    participantList.forEach((participant: Participant) => {
      participantConfigInitialValues[participant.pure_domain_name] = {
        loss_type: formConfig?.loss_type,
        algorithmProjectUuid:
          modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects[
            participant.pure_domain_name
          ],
        nn_config: baseNN,
        tree_config: baseTree,
      };
    });
    return participantConfigInitialValues;
  }, [
    stepTwoFormConfig,
    participantList,
    formConfig?.loss_type,
    modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects,
    baseNN,
    baseTree,
  ]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const lastModelJobQuery = useQuery(
    [
      'fetchLastAutoUpdateModelJob',
      projectId,
      modelGroupDetail?.id!,
      modelGroupDetail?.auto_update_status,
    ],
    () => fetchAutoUpdateModelJobDetail(projectId!, modelGroupDetail?.id!),
    {
      enabled:
        jobType === 'repeat' &&
        !!projectId &&
        !!modelGroupDetail?.id &&
        modelGroupDetail?.auto_update_status === AutoModelJobStatus.STOPPED,
      retry: 1,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        const modelJobDetail = res.data;
        const variablesList = ['loss_type', 'role'];
        const sourceList = [
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
        const globalConfig = modelJobDetail.global_config?.global_config;
        const coordinatorConfig = globalConfig?.[myPureDomainName];
        const coordinatorMapValue = getConfigInitialValuesByDefinition(
          coordinatorConfig?.variables!,
          variablesList,
        );
        const coordinatorSource = getConfigInitialValuesByDefinition(
          coordinatorConfig?.variables!,
          sourceList,
        );

        const participantConfig: Record<string, any> = {};
        participantList.forEach((participant: Participant) => {
          const curParticipantConfig = globalConfig?.[participant.pure_domain_name];
          const curParticipantSource = getConfigInitialValuesByDefinition(
            curParticipantConfig?.variables!,
            sourceList,
          );
          participantConfig[participant.pure_domain_name] = {
            loss_type: coordinatorMapValue?.loss_type,
            algorithmProjectUuid:
              modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects[
                participant.pure_domain_name
              ],
            algorithm: {
              algorithmUuid: curParticipantConfig?.algorithm_uuid,
              config: curParticipantConfig?.algorithm_parameter?.variables,
            },
            nn_config: {
              ...baseNN,
              ...getNNBaseConfigInitialValuesByDefinition(curParticipantConfig?.variables!),
              ...getAdvanceConfigListByDefinition(curParticipantConfig?.variables!, true).reduce(
                (acc, cur) => {
                  acc[cur.field!] = cur.initialValue;
                  return acc;
                },
                {} as any,
              ),
            },
            tree_config: {
              ...baseTree,
              ...getTreeBaseConfigInitialValuesByDefinition(curParticipantConfig?.variables!),
              ...getAdvanceConfigListByDefinition(curParticipantConfig?.variables!).reduce(
                (acc, cur) => {
                  acc[cur.field!] = cur.initialValue;
                  return acc;
                },
                {} as any,
              ),
            },
            source_config: curParticipantSource,
          };
        });

        setFormConfig({
          name: `${modelGroupDetail?.name}-v${modelGroupDetail?.latest_version! + 1}`,
          algorithmProjects: modelGroupDetail?.algorithm_project_uuid_list?.algorithm_projects,
          data_batch_id: modelJobDetail.data_batch_id || undefined,
          loss_type: coordinatorMapValue.loss_type,
          role: coordinatorMapValue.role,
          [myPureDomainName]: {
            algorithm: {
              algorithmUuid: coordinatorConfig?.algorithm_uuid,
              config: coordinatorConfig?.algorithm_parameter?.variables,
            },
          },
          nn_config: {
            ...baseNN,
            ...getNNBaseConfigInitialValuesByDefinition(coordinatorConfig?.variables!),
            ...getAdvanceConfigListByDefinition(coordinatorConfig?.variables!, true).reduce(
              (acc, cur) => {
                acc[cur.field!] = cur.initialValue;
                return acc;
              },
              {} as any,
            ),
          },
          tree_config: {
            ...baseTree,
            ...getTreeBaseConfigInitialValuesByDefinition(coordinatorConfig?.variables!),
            ...getAdvanceConfigListByDefinition(coordinatorConfig?.variables!).reduce(
              (acc, cur) => {
                acc[cur.field!] = cur.initialValue;
                return acc;
              },
              {} as any,
            ),
          },
          resource_config: coordinatorSource,
        });
        setStepTwoFormConfig(participantConfig);
      },
      onError: () => {
        Message.info('获取历史定时续训任务配置失败，请重新填写配置信息！');
      },
    },
  );

  useEffect(() => {
    setCurrentStep(CreateSteps[createStep || 'coordinator']);
  }, [createStep]);

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={() => history.goBack()} isShowConfirmModal={isFormValueChanged}>
          {modelGroupDetail?.name}
        </BackButton>
      }
      centerTitle={
        jobType === 'repeat'
          ? modelGroupDetail?.auto_update_status === AutoModelJobStatus.STOPPED
            ? '配置定时续训任务'
            : '创建定时续训任务'
          : '创建新任务'
      }
    >
      <Row justify="center">
        <Steps className={styles.step_container} current={currentStep} size="small">
          <Step title="我方配置" />
          <Step title="合作伙伴配置" />
        </Steps>
      </Row>
      <section className={styles.form_area}>
        <Route
          path={generatePath(routes.ModelTrainJobCreate, {
            id: modelGroupId,
            type: jobType,
            step: 'coordinator',
          })}
          exact
          render={() => (
            <StepOneCoordinator
              isLoading={modelGroupDetailQuery.isFetching || datasetDetailQuery.isFetching}
              onFormValueChange={onFormValueChange}
              modelGroup={modelGroupDetail}
              jobType={jobType}
              datasetName={datasetDetail?.name}
              formInitialValues={stepOneInitialValues}
              isFormValueChanged={isFormValueChanged}
              onFirstStepSubmit={(value) => setFormConfig(value)}
              treeAdvancedFormItemList={treeAdvancedFormItemList}
              nnAdvancedFormItemList={nnAdvancedFormItemList}
              algorithmProjectList={algorithmProjectList}
              peerAlgorithmProjectList={peerAlgorithmProjectList}
              datasetBatchType={datasetJob?.time_range?.hours === 1 ? 'hour' : 'day'}
            />
          )}
        />
        <Route
          path={generatePath(routes.ModelTrainJobCreate, {
            id: modelGroupId,
            type: jobType,
            step: 'participant',
          })}
          exact
          render={() => (
            <StepTwoParticipant
              modelGroup={modelGroupDetail}
              formInitialValues={stepTwoInitialValues}
              isFormValueChanged={isFormValueChanged}
              stepOneFormConfigValues={formConfig}
              onFormValueChange={onFormValueChange}
              onSecondStepSubmit={(value) => {
                createTrainModelJob(value);
              }}
              saveStepTwoValues={(value) => setStepTwoFormConfig(value)}
              treeAdvancedFormItemList={treeAdvancedFormItemList}
              nnAdvancedFormItemList={nnAdvancedFormItemList}
              algorithmProjectList={algorithmProjectList}
              peerAlgorithmProjectList={peerAlgorithmProjectList}
              submitLoading={submitLoading}
            />
          )}
        />
      </section>
    </SharedPageLayout>
  );

  async function createTrainModelJob(value: any) {
    setSubmitLoading(true);
    if (!projectId) {
      return Message.info('请选择工作区！');
    }

    const isTree = isTreeAlgorithm(modelGroupDetail?.algorithm_type as EnumAlgorithmProjectType);
    const coordinatorConfigValues = formConfig;
    const participantsConfigValues = value;
    const metricIsPublic = value.metric_is_public;
    const participantsPayload: Record<string, any> = {};
    const participantRole =
      modelGroupDetail?.algorithm_type === EnumAlgorithmProjectType.NN_HORIZONTAL
        ? TrainRoleType.FEATURE
        : coordinatorConfigValues?.role === TrainRoleType.FEATURE
        ? TrainRoleType.LABEL
        : TrainRoleType.FEATURE;
    participantList.forEach((participant: Participant) => {
      const curParticipantConfig = participantsConfigValues?.[participant.pure_domain_name];
      participantsPayload[participant.pure_domain_name] = isTree
        ? {
            variables: hydrateModalGlobalConfig(modelJobDefinition?.variables!, {
              role: participantRole,
              loss_type: coordinatorConfigValues?.loss_type,
              ...curParticipantConfig?.tree_config,
              ...curParticipantConfig?.resource_config,
            }),
          }
        : {
            algorithm_uuid: curParticipantConfig?.algorithm?.algorithmUuid,
            algorithm_parameter: { variables: curParticipantConfig?.algorithm?.config },
            variables: hydrateModalGlobalConfig(modelJobDefinition?.variables!, {
              role: participantRole,
              ...curParticipantConfig?.nn_config,
              ...curParticipantConfig?.resource_config,
            }),
          };
    });
    try {
      const res = await createModelJob(projectId, {
        name: `${modelGroupDetail?.name}-v${modelGroupDetail?.latest_version! + 1}`,
        comment: coordinatorConfigValues?.comment,
        group_id: modelGroupDetail?.id,
        model_job_type: EnumModelJobType.TRAINING,
        algorithm_type: modelGroupDetail?.algorithm_type as EnumAlgorithmProjectType,
        data_batch_id: coordinatorConfigValues?.data_batch_id,
        global_config: {
          dataset_uuid: datasetDetail?.uuid,
          global_config: {
            [myPureDomainName]: isTree
              ? {
                  variables: hydrateModalGlobalConfig(modelJobDefinition?.variables!, {
                    role: coordinatorConfigValues?.role,
                    loss_type: coordinatorConfigValues?.loss_type,
                    ...coordinatorConfigValues?.tree_config,
                    ...coordinatorConfigValues?.resource_config,
                  }),
                }
              : {
                  algorithm_uuid:
                    coordinatorConfigValues?.[myPureDomainName].algorithm?.algorithmUuid,
                  algorithm_parameter: {
                    variables: coordinatorConfigValues?.[myPureDomainName].algorithm?.config,
                  },
                  variables: hydrateModalGlobalConfig(modelJobDefinition?.variables!, {
                    role: coordinatorConfigValues?.role,
                    ...coordinatorConfigValues?.nn_config,
                    ...coordinatorConfigValues?.resource_config,
                  }),
                },
            ...participantsPayload,
          },
        },
      });
      metricIsPublic &&
        (await updateModelJob(projectId, res.data.id, { metric_is_public: metricIsPublic }));
      Message.success(
        jobType === 'repeat'
          ? modelGroupDetail?.auto_update_status === AutoModelJobStatus.STOPPED
            ? '配置定时续训任务成功！'
            : '创建定时续训任务成功！'
          : '创建模型训练任务成功！',
      );
      setSubmitLoading(false);
      history.push(
        generatePath(routes.ModelTrainDetail, {
          id: modelGroupDetail?.id,
        }),
      );
    } catch (error: any) {
      Message.error(error.message);
    }
  }
}

export default ModelTrainJobCreate;
