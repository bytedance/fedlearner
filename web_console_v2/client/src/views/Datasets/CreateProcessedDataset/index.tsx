import {
  Alert,
  Button,
  Form,
  Input,
  Message,
  Space,
  Spin,
  Tag,
  Switch,
  Card,
} from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';
import BlockRadio from 'components/_base/BlockRadio';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import DatasetSelect from 'components/DatasetSelect';
import DatasetInfo from './DatasetInfo';
import ConfigForm, { ExposedRef, ItemProps } from 'components/ConfigForm';
import { Tag as TagEnum } from 'typings/workflow';
import React, { FC, useEffect, useMemo, useRef, useState } from 'react';
import { useHistory, useParams } from 'react-router';
import {
  createDatasetJobs,
  createDataset,
  fetchDataJobVariableDetail,
  fetchDatasetDetail,
  fetchDatasetJobDetail,
  authorizeDataset,
} from 'services/dataset';
import { fetchSysInfo } from 'services/settings';
import { isStringCanBeParsed, to } from 'shared/helpers';
import {
  useGetAppFlagValue,
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useIsFormValueChange,
  useGetCurrentProjectAbilityConfig,
} from 'hooks';
import { MAX_COMMENT_LENGTH, validNamePattern } from 'shared/validator';
import TitleWithIcon from 'components/TitleWithIcon';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { useQuery } from 'react-query';
import FormLabel from 'components/FormLabel';
import { LabelStrong } from 'styles/elements';
import {
  DataJobBackEndType,
  DataJobType,
  DataJobVariable,
  DataJoinType,
  Dataset,
  DatasetJobCreatePayload,
  DatasetCreatePayload,
  DatasetKindV2,
  DATASET_COPY_CHECKER,
  DataSourceStructDataType,
  DataJoinToolTipText,
  DatasetType,
  DatasetDataType,
  DatasetType__archived,
  DatasetKindBackEndType,
} from 'typings/dataset';
import {
  Variable,
  VariableComponent,
  VariableValueType,
  VariableWidgetSchema,
} from 'typings/variable';
import { Participant, ParticipantType } from 'typings/participant';
import { hydrate } from 'views/Workflows/shared';
import {
  NO_CATEGORY,
  SYNCHRONIZATION_VARIABLE,
  TAG_MAPPER,
  VARIABLE_TIPS_MAPPER,
  isDataAlignment,
  isDataLightClient,
  isDataOtPsiJoin,
  isDataHashJoin,
  isHoursCronJoin,
  CronType,
  cronTypeOptions,
} from '../shared';
import Title from './TitleWithRecommendedParam';
import { FlagKey } from 'typings/flag';
import styled from './index.module.less';

type Props = Record<string, unknown>;
type Params = {
  [key: string]: any;
};

type FormData = {
  name: string;
  comment: string;
  data_job_type: DataJobType;
  data_join_type: DataJoinType;
  dataset_info: Dataset;
  params: Params;
  cron_type: CronType;
  participant: {
    [participantName: string]: {
      dataset_info: Dataset;
      params: Params;
    };
  };
};

type DataJoinTypeOption = {
  value: `${DataJoinType}`;
  label: string;
  tooltip?: string;
};

const dataJoinTypeOptionLightClient = [
  {
    value: DataJoinType.LIGHT_CLIENT,
    label: 'RSA-PSI 求交',
  },
  {
    value: DataJoinType.LIGHT_CLIENT_OT_PSI_DATA_JOIN,
    label: 'OT-PSI 求交',
  },
];

const initialFormValues: Partial<FormData> = {
  name: '',
  data_join_type: DataJoinType.PSI,
  cron_type: CronType.DAY,
};

const CreateDataset: FC<Props> = () => {
  const { id, action } = useParams<{
    action: 'create' | 'edit' | 'authorize';
    id: string;
  }>();
  const isAuthorize = action === 'authorize';
  const [formInstance] = Form.useForm<FormData>();
  const history = useHistory();
  const hash_data_join_enabled = useGetAppFlagValue(FlagKey.HASH_DATA_JOIN_ENABLED);
  const participantList = useGetCurrentProjectParticipantList();
  const { hasIdAlign, hasVertical, hasHorizontal } = useGetCurrentProjectAbilityConfig();

  const [dataJobType, setDataJobType] = useState<DataJobType>(
    initialFormValues?.data_job_type ?? DataJobType.JOIN,
  );
  const [dataJoinType, setDataJoinType] = useState<DataJoinType>(
    initialFormValues?.data_join_type ?? DataJoinType.PSI,
  );
  const [isDoing, setIsDoing] = useState(false);
  const [isCron, setIsCron] = useState(false);
  const [cronType, setCornType] = useState<CronType>(initialFormValues?.cron_type ?? CronType.DAY);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange();
  const currentProjectId = useGetCurrentProjectId();
  const configFormRefList = useRef<Array<ExposedRef | null>>([]);
  const [globalConfigMap, setGlobalConfigMap] = useState<any>();

  const finalDataJobType = useMemo<DataJobBackEndType>(() => {
    if (dataJobType === DataJobType.ALIGNMENT) {
      return DataJobBackEndType.DATA_ALIGNMENT;
    }
    if (dataJoinType === DataJoinType.LIGHT_CLIENT) {
      return DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN;
    }
    if (dataJoinType === DataJoinType.LIGHT_CLIENT_OT_PSI_DATA_JOIN) {
      return DataJobBackEndType.LIGHT_CLIENT_OT_PSI_DATA_JOIN;
    }
    if (dataJoinType === DataJoinType.OT_PSI_DATA_JOIN) {
      return DataJobBackEndType.OT_PSI_DATA_JOIN;
    }
    if (dataJoinType === DataJoinType.HASH_DATA_JOIN) {
      return DataJobBackEndType.HASH_DATA_JOIN;
    }
    return dataJoinType === DataJoinType.PSI
      ? DataJobBackEndType.RSA_PSI_DATA_JOIN
      : DataJobBackEndType.DATA_JOIN;
  }, [dataJobType, dataJoinType]);

  // ======= Dataset query ============
  const datasetQuery = useQuery(['fetchDatasetDetail', id], () => fetchDatasetDetail(id), {
    refetchOnWindowFocus: false,
    retry: 2,
    enabled: isAuthorize && Boolean(id),
  });

  // 获取当前数据任务信息， 包括本方和合作伙伴方
  const datasetJobDetailQuery = useQuery(
    ['fetchDatasetJobDetail', currentProjectId, datasetQuery.data?.data.parent_dataset_job_id],
    () => fetchDatasetJobDetail(currentProjectId!, datasetQuery.data?.data.parent_dataset_job_id!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled:
        isAuthorize && Boolean(currentProjectId && datasetQuery.data?.data.parent_dataset_job_id),
      onSuccess(res) {
        const {
          name,
          kind,
          global_configs: { global_configs },
        } = res.data;
        const { comment, dataset_type } = datasetQuery.data?.data!;
        if (!isAuthorize) return;
        // 设置参数信息， 支持多方
        Object.keys(global_configs).forEach((key) => {
          const globalConfig = global_configs[key];
          (globalConfig as any).variables = handleParseToConfigFrom(
            handleParseDefinition(globalConfig.variables),
            isAuthorize,
          );
        });
        setGlobalConfigMap(global_configs);

        setDataJobType(isDataAlignment(kind) ? DataJobType.ALIGNMENT : DataJobType.JOIN);
        setDataJoinType(
          isDataLightClient(kind)
            ? DataJoinType.LIGHT_CLIENT
            : isDataOtPsiJoin(kind)
            ? DataJoinType.OT_PSI_DATA_JOIN
            : isDataHashJoin(kind)
            ? DataJoinType.HASH_DATA_JOIN
            : DataJoinType.PSI,
        );
        setIsCron(dataset_type === DatasetType__archived.STREAMING);
        isHoursCronJoin(res.data) ? setCornType(CronType.HOUR) : setCornType(CronType.DAY);
        formInstance.setFieldsValue({
          name,
          comment,
          data_job_type: isDataAlignment(kind) ? DataJobType.ALIGNMENT : DataJobType.JOIN,
          data_join_type: isDataLightClient(kind)
            ? DataJoinType.LIGHT_CLIENT
            : isDataOtPsiJoin(kind)
            ? DataJoinType.OT_PSI_DATA_JOIN
            : isDataHashJoin(kind)
            ? DataJoinType.HASH_DATA_JOIN
            : DataJoinType.PSI,
        });
      },
    },
  );

  const dataJobVariableDetailQuery = useQuery(
    ['fetchDataJobVariableDetail', finalDataJobType],
    () => fetchDataJobVariableDetail(finalDataJobType),
    {
      enabled: !isAuthorize && Boolean(finalDataJobType),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const sysInfoQuery = useQuery(['fetchSysInfo'], () => fetchSysInfo(), {
    retry: 2,
    refetchOnWindowFocus: false,
  });

  const myDomainName = useMemo<string>(() => {
    return sysInfoQuery.data?.data?.domain_name ?? '';
  }, [sysInfoQuery.data]);

  const myPureDomainName = useMemo<string>(() => {
    return sysInfoQuery.data?.data?.pure_domain_name ?? '';
  }, [sysInfoQuery.data]);

  const participantName = useMemo<string>(() => {
    if (!datasetJobDetailQuery.data?.data.coordinator_id) return '';
    const participant = participantList.find(
      (item) => item.id === datasetJobDetailQuery.data?.data.coordinator_id,
    );
    return participant?.pure_domain_name ?? '';
  }, [datasetJobDetailQuery.data, participantList]);

  const dataJobVariableList = useMemo<Variable[]>(() => {
    if (!dataJobVariableDetailQuery.data?.data?.variables) {
      return [];
    }
    return handleParseDefinition(dataJobVariableDetailQuery.data.data.variables);
  }, [dataJobVariableDetailQuery.data]);

  const datasetSelectFilterOptions = useMemo(() => {
    // todo: 目前对齐要求只展示非增量数据集， 后续这块逻辑需要优化
    const options: any = {
      dataset_type: DatasetType.PSI,
      dataset_format: [DatasetDataType.STRUCT, DatasetDataType.PICTURE],
      dataset_kind: [DatasetKindBackEndType.RAW, DatasetKindBackEndType.PROCESSED],
    };
    if (isCron) {
      options.dataset_type = DatasetType.STREAMING;
      options.cron_interval = [cronType === CronType.DAY ? 'DAYS' : 'HOURS'];
    }
    return options;
  }, [isCron, cronType]);

  const [paramsList, collapseParamsList] = useMemo(() => {
    return handleParseToConfigFrom(dataJobVariableList, isAuthorize);
  }, [dataJobVariableList, isAuthorize]);

  const dataJobTypeOptionsGenerator = useMemo(() => {
    const dataJobTypeOptions = [];
    if (hasIdAlign || hasVertical) {
      dataJobTypeOptions.push({
        value: DataJobType.JOIN,
        label: hasIdAlign ? '轻客户端求交' : '求交',
      });
    }
    if (hasHorizontal) {
      dataJobTypeOptions.push({
        value: DataJobType.ALIGNMENT,
        label: '对齐',
      });
    }
    return dataJobTypeOptions;
  }, [hasIdAlign, hasVertical, hasHorizontal]);

  const dataJoinTypeOptionsGenerator = useMemo(() => {
    const dataJoinTypeOptions: DataJoinTypeOption[] = [
      {
        value: DataJoinType.OT_PSI_DATA_JOIN,
        label: 'OT-PSI 求交',
        tooltip: DataJoinToolTipText.OT_PSI_DATA_JOIN,
      },
      {
        value: DataJoinType.PSI,
        label: 'RSA-PSI 求交',
        tooltip: DataJoinToolTipText.PSI,
      },
    ];
    if (hash_data_join_enabled) {
      dataJoinTypeOptions.push({
        value: DataJoinType.HASH_DATA_JOIN,
        label: '哈希求交',
        tooltip: DataJoinToolTipText.HASH_DATA_JOIN,
      });
    }
    if (hasIdAlign) {
      return dataJoinTypeOptionLightClient;
    }
    if (hasVertical) {
      return dataJoinTypeOptions;
    }
    return dataJoinTypeOptions;
  }, [hash_data_join_enabled, hasIdAlign, hasVertical]);

  useEffect(() => {
    const defaultJoinType = dataJoinTypeOptionsGenerator[0]?.value as DataJoinType;
    const defaultJobType = dataJobTypeOptionsGenerator[0]?.value;
    formInstance.setFieldsValue({
      data_join_type: defaultJoinType,
      data_job_type: defaultJobType,
    });
    setDataJoinType(defaultJoinType);
    setDataJobType(defaultJobType);
  }, [dataJobTypeOptionsGenerator, dataJoinTypeOptionsGenerator, formInstance]);

  const authorizeDataJobType = useMemo(() => {
    return dataJobTypeOptionsGenerator.find((item) => item.value === dataJobType)?.label;
  }, [dataJobType, dataJobTypeOptionsGenerator]);

  const authorizeDataJoinType = useMemo(() => {
    return (dataJoinTypeOptionsGenerator as DataJoinTypeOption[]).find(
      (item) => item.value === dataJoinType,
    )?.label;
  }, [dataJoinType, dataJoinTypeOptionsGenerator]);

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={backToList} isShowConfirmModal={isFormValueChanged}>
          结果数据集
        </BackButton>
      }
      contentWrapByCard={false}
      centerTitle={isAuthorize ? '授权结果数据集' : '创建数据集'}
    >
      <Spin loading={dataJobVariableDetailQuery.isFetching || datasetJobDetailQuery.isFetching}>
        {isAuthorize && renderBannerCard()}
        {renderCardFrom()}
      </Spin>
    </SharedPageLayout>
  );

  function renderBannerCard() {
    const title = `${participantName}向您发起${datasetJobDetailQuery.data?.data.name}的数据集授权申请`;
    return (
      <Card className="card" bordered={false} style={{ marginBottom: 20 }}>
        <Space size="medium">
          <div className={styled.dataset_processed_avatar} />
          <>
            <LabelStrong fontSize={16}>{title}</LabelStrong>
            <TitleWithIcon
              title="确认授权后，数据任务将自动运行，可在结果数据集页查看详细信息。"
              isLeftIcon={true}
              isShowIcon={true}
              icon={IconInfoCircle}
            />
          </>
        </Space>
      </Card>
    );
  }

  function renderCardFrom() {
    return (
      <Card className={styled.dataset_processed_card} bordered={false}>
        <Form
          className={styled.dataset_processed_create_form}
          disabled={isAuthorize}
          initialValues={initialFormValues}
          form={formInstance}
          onSubmit={onSubmit}
          onValuesChange={onFormValueChange}
          scrollToFirstError={true}
        >
          {renderBaseConfigLayout()}
          {renderParticipantConfigLayout()}
          {renderFooterButton()}
        </Form>
      </Card>
    );
  }

  function renderBaseConfigLayout() {
    return (
      <section className={styled.dataset_processed_create_section}>
        <h3>基本配置</h3>
        <Form.Item
          field="name"
          label="数据集名称"
          hasFeedback
          rules={[
            { required: true, message: '请输入' },
            {
              match: validNamePattern,
              message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
            },
          ]}
        >
          <Input placeholder="请输入" maxLength={60} />
        </Form.Item>
        <Form.Item
          field="comment"
          label="数据集描述"
          rules={[{ maxLength: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }]}
        >
          <Input.TextArea rows={3} placeholder="最多为 200 个字符" showWordLimit />
        </Form.Item>
        <Form.Item field="data_job_type" label="数据任务" rules={[{ required: true }]}>
          {isAuthorize ? (
            <div className={styled.dataset_processed_desc}>{authorizeDataJobType}</div>
          ) : (
            <BlockRadio
              flexGrow={0}
              isCenter={true}
              isOneHalfMode={false}
              options={dataJobTypeOptionsGenerator}
              onChange={(val: DataJobType) => {
                setDataJobType(val);
                setIsCron(false);
              }}
            />
          )}
        </Form.Item>
        {dataJobType === DataJobType.JOIN && (
          <Form.Item field="data_join_type" label="求交方式" rules={[{ required: true }]}>
            {isAuthorize ? (
              <div className={styled.dataset_processed_desc}>{authorizeDataJoinType}</div>
            ) : (
              <BlockRadio.WithToolTip
                flexGrow={0}
                isCenter={true}
                isOneHalfMode={false}
                options={dataJoinTypeOptionsGenerator}
                onChange={(val: DataJoinType) => {
                  setDataJoinType(val);
                }}
              />
            )}
          </Form.Item>
        )}
        {!hasIdAlign && dataJobType === DataJobType.JOIN && (
          <Form.Item field="is_cron" label="定时求交">
            {isAuthorize ? (
              <div className={styled.dataset_processed_desc}>{isCron ? '已开启' : '未开启'}</div>
            ) : (
              <Space>
                <Switch onChange={handleCronChange} />
                <TitleWithIcon
                  title="开启后仅支持选择增量数据集"
                  isLeftIcon={true}
                  isShowIcon={true}
                  icon={IconInfoCircle}
                />
              </Space>
            )}
          </Form.Item>
        )}
        {dataJobType === DataJobType.JOIN && isCron && (
          <Form.Item
            field="cron_type"
            label={
              <FormLabel
                className={styled.dataset_processed_form_label}
                label="求交周期"
                tooltip="会在提交后立即求交，后续任务将按照设定的时间定期进行"
              />
            }
          >
            {isAuthorize ? (
              <div className={styled.dataset_processed_desc}>
                {cronType === CronType.DAY ? '每天' : '每小时'}
              </div>
            ) : (
              <BlockRadio
                flexGrow={0}
                isCenter={false}
                isOneHalfMode={false}
                options={cronTypeOptions}
                onChange={(val: CronType) => {
                  handleCronTypeChange(val);
                }}
              />
            )}
          </Form.Item>
        )}
        {isAuthorize ? (
          <Form.Item
            field="dataset_info"
            label="我方数据集"
            rules={[{ required: true, message: '请选择' }]}
          >
            <DatasetInfo
              isParticipant={false}
              datasetUuid={
                isAuthorize && globalConfigMap?.[myPureDomainName]?.dataset_uuid
                  ? globalConfigMap[myPureDomainName].dataset_uuid
                  : ''
              }
            />
          </Form.Item>
        ) : (
          <Form.Item
            field="dataset_info"
            label="我方数据集"
            rules={[{ required: true, message: '请选择' }]}
          >
            <DatasetSelect
              lazyLoad={{
                enable: true,
                page_size: 10,
              }}
              filterOptions={datasetSelectFilterOptions}
              isParticipant={false}
            />
          </Form.Item>
        )}
        <Form.Item field="params" label="我方参数">
          {dataJobVariableDetailQuery.isError ? (
            <Alert type="info" content="暂不支持该类型的数据任务" />
          ) : (
            <ConfigForm
              filter={variableTagFilter}
              groupBy={'tag'}
              hiddenGroupTag={false}
              cols={2}
              configFormExtra={
                dataJobType === DataJobType.JOIN ? <Title joinType={dataJoinType} /> : undefined
              }
              formProps={{
                style: {
                  marginTop: 7,
                },
              }}
              formItemList={
                isAuthorize
                  ? globalConfigMap && globalConfigMap[myPureDomainName]
                    ? globalConfigMap[myPureDomainName].variables[0]
                    : []
                  : paramsList
              }
              collapseFormItemList={
                isAuthorize
                  ? globalConfigMap && globalConfigMap[myPureDomainName]
                    ? globalConfigMap[myPureDomainName].variables[1]
                    : []
                  : collapseParamsList
              }
              ref={(ref) => {
                configFormRefList.current[0] = ref;
              }}
              isResetOnFormItemListChange={true}
              onChange={(val) => {
                syncConfigFormValue(
                  val,
                  [
                    SYNCHRONIZATION_VARIABLE.NUM_PARTITIONS,
                    SYNCHRONIZATION_VARIABLE.PART_NUM,
                    SYNCHRONIZATION_VARIABLE.REPLICAS,
                  ],
                  false,
                );
              }}
            />
          )}
        </Form.Item>
      </section>
    );
  }

  function variableTagFilter(item: ItemProps) {
    return (
      !!item.tag &&
      [TAG_MAPPER[TagEnum.INPUT_PARAM], TAG_MAPPER[TagEnum.RESOURCE_ALLOCATION]].includes(item.tag)
    );
  }

  function renderParticipantConfigLayout() {
    return participantList?.map((item, index) => {
      const { type, pure_domain_name, id } = item;
      const isLightClient = type === ParticipantType.LIGHT_CLIENT;
      return isLightClient ? (
        renderLightClientInfo(item)
      ) : (
        <section key={item.domain_name}>
          <h3>{item.name}</h3>
          {isAuthorize ? (
            <Form.Item
              field={`participant.${item.name}.dataset_info`}
              label={`合作伙伴数据集`}
              rules={[{ required: true, message: '请选择' }]}
            >
              <DatasetInfo
                isParticipant={true}
                participantId={id}
                datasetUuid={
                  isAuthorize && globalConfigMap?.[pure_domain_name!]?.dataset_uuid
                    ? globalConfigMap[pure_domain_name!].dataset_uuid
                    : ''
                }
              />
            </Form.Item>
          ) : (
            <Form.Item
              field={`participant.${item.name}.dataset_info`}
              label={`合作伙伴数据集`}
              rules={[{ required: true, message: '请选择' }]}
            >
              <DatasetSelect
                queryParams={{
                  //TODO Temporarily obtain full data and will be removed soon
                  participant_id: id,
                  page_size: 0,
                }}
                filterOptions={datasetSelectFilterOptions}
                isParticipant={true}
              />
            </Form.Item>
          )}
          <Form.Item field={`participant.${item.name}.params`} label={`合作伙伴参数`}>
            {dataJobVariableDetailQuery.isError ? (
              <Alert type="info" content="暂不支持该类型的数据任务" />
            ) : (
              <ConfigForm
                filter={variableTagFilter}
                groupBy={'tag'}
                hiddenGroupTag={false}
                cols={2}
                configFormExtra={
                  dataJobType === DataJobType.JOIN ? <Title joinType={dataJoinType} /> : undefined
                }
                formProps={{
                  style: {
                    marginTop: 7,
                  },
                }}
                formItemList={
                  isAuthorize
                    ? globalConfigMap && globalConfigMap[myPureDomainName]
                      ? globalConfigMap[myPureDomainName].variables[0]
                      : []
                    : paramsList
                }
                collapseFormItemList={
                  isAuthorize
                    ? globalConfigMap && globalConfigMap[myPureDomainName]
                      ? globalConfigMap[myPureDomainName].variables[1]
                      : []
                    : collapseParamsList
                }
                ref={(ref) => {
                  configFormRefList.current[index + 1] = ref;
                }}
                isResetOnFormItemListChange={true}
                onChange={(val) => {
                  syncConfigFormValue(
                    val,
                    [
                      SYNCHRONIZATION_VARIABLE.NUM_PARTITIONS,
                      SYNCHRONIZATION_VARIABLE.PART_NUM,
                      SYNCHRONIZATION_VARIABLE.REPLICAS,
                    ],
                    true,
                    item.name,
                  );
                }}
              />
            )}
          </Form.Item>
        </section>
      );
    });
  }

  function renderFooterButton() {
    return (
      <Space className={styled.dataset_processed_footer_button}>
        {isAuthorize ? (
          <Button type="primary" loading={isDoing} onClick={onAuthorize}>
            确认授权
          </Button>
        ) : (
          <Button
            type="primary"
            htmlType="submit"
            loading={isDoing}
            disabled={dataJobVariableDetailQuery.isError}
          >
            确认创建
          </Button>
        )}

        <ButtonWithModalConfirm onClick={backToList} isShowConfirmModal={isFormValueChanged}>
          取消
        </ButtonWithModalConfirm>
      </Space>
    );
  }

  function renderLightClientInfo(lightClientInfo: Participant) {
    return (
      <section key={lightClientInfo.domain_name}>
        <h3>
          {' '}
          {lightClientInfo.domain_name}
          <Tag className={styled.title_tag} color="arcoblue">
            轻量
          </Tag>
        </h3>
        <Form.Item
          field={`participant.${lightClientInfo.name}.dataset_info`}
          label="合作伙伴数据集"
          rules={[{ message: '请选择' }]}
        >
          <div>由客户侧本地上传</div>
        </Form.Item>
      </section>
    );
  }

  function backToList() {
    history.goBack();
  }

  function handleParseDefinition(definitions: DataJobVariable[]) {
    return definitions.map((item) => {
      let widget_schema: VariableWidgetSchema = {};

      try {
        widget_schema = JSON.parse(item.widget_schema);
      } catch (error) {}
      return {
        ...item,
        widget_schema,
      };
    });
  }

  function handleParseToConfigFrom(variableList: Variable[], disabled: boolean) {
    const formItemList: ItemProps[] = [];
    const collapseFormItemList: ItemProps[] = [];
    variableList
      .filter((item) => !item.widget_schema.hidden)
      .forEach((item) => {
        const baseRuleList = item.widget_schema.required
          ? [
              {
                required: true,
                message: '必填项',
              },
            ]
          : [];
        const formItemConfig = {
          disabled, // 在授权时将参数配置禁用修改
          tip: VARIABLE_TIPS_MAPPER[item.name],
          label: item.name,
          tag: TAG_MAPPER[item.tag as TagEnum] || NO_CATEGORY,
          field: item.name,
          initialValue:
            item.widget_schema.component === VariableComponent.Input
              ? item.value
              : item.typed_value,
          componentType: item.widget_schema.component,
          rules:
            item.widget_schema.component === VariableComponent.Input &&
            [VariableValueType.LIST, VariableValueType.OBJECT].includes(item.value_type!)
              ? [
                  ...baseRuleList,
                  {
                    validator: (value: any, callback: (error?: string | undefined) => void) => {
                      if ((value && typeof value === 'object') || isStringCanBeParsed(value)) {
                        callback();
                        return;
                      }
                      callback(`JSON ${item.value_type!} 格式错误`);
                    },
                  },
                ]
              : baseRuleList,
        };

        if (formItemConfig.tag === TAG_MAPPER[TagEnum.INPUT_PARAM]) {
          formItemList.push(formItemConfig);
        }
        if (formItemConfig.tag === TAG_MAPPER[TagEnum.RESOURCE_ALLOCATION]) {
          collapseFormItemList.push(formItemConfig);
        }
      });

    return [formItemList, collapseFormItemList];
  }

  /**
   * This function is used to synchronize advanced parameters of the sender and participants(at least one participant)
   * @param value config values;
   * @param keyList the variable name needs to be kept same;
   * @param isParticipant is called by participant ro not;
   * @param currentParticipant current participant name;
   */
  function syncConfigFormValue(
    value: { [prop: string]: any },
    keyList: string[],
    isParticipant: boolean,
    currentParticipant?: string,
  ) {
    if (!keyList || !keyList.length || !value) {
      return;
    }
    const senderParams: any = formInstance.getFieldValue('params') || {};
    const participantParams: any = formInstance.getFieldValue('participant');
    keyList.forEach((key) => {
      if (!Object.prototype.hasOwnProperty.call(value, key)) {
        return;
      }
      if (isParticipant) {
        senderParams[key] = value[key];
      }
      participantList.forEach((item) => {
        if (isParticipant && item.name === currentParticipant) {
          return;
        }
        const params = participantParams?.[item.name]?.params || {};
        params[key] = value[key];
      });
    });
    formInstance.setFieldsValue({
      params: {
        ...senderParams,
      },
      participant: {
        ...participantParams,
      },
    });
  }

  function handleCronChange(value: boolean) {
    // 切换定时求交之后， 需要将之前选中的数据集内容清空掉
    formInstance.setFieldValue('dataset_info', {});
    participantList.forEach((item) => {
      formInstance.setFieldValue(`participant.${item.name}.dataset_info` as keyof FormData, {});
    });
    setIsCron(value);
    setCornType(CronType.DAY);
  }

  function handleCronTypeChange(value: CronType) {
    // 切换定时求交之后， 需要将之前选中的数据集内容清空掉
    formInstance.setFieldValue('dataset_info', {});
    participantList.forEach((item) => {
      formInstance.setFieldValue(`participant.${item.name}.dataset_info` as keyof FormData, {});
    });
    setCornType(value);
  }

  async function onSubmit(values: FormData) {
    if (!currentProjectId) {
      return Message.error('请选择工作区');
    }
    if (!myDomainName) {
      return Message.error('获取本系统 domain_name 失败');
    }

    // Validate <ConfigForm/> form
    try {
      await Promise.all(
        configFormRefList.current.filter((i) => i).map((i) => i?.formInstance.validate()),
      );
    } catch (error) {
      return Message.info('必填项');
    }

    setIsDoing(true);

    const { dataset_type, dataset_format, store_format, import_type } = formInstance.getFieldValue(
      'dataset_info',
    ) as Dataset;

    // create dataset
    const [res, addDataSetError] = await to(
      createDataset({
        kind: DatasetKindV2.PROCESSED,
        project_id: currentProjectId,
        name: values.name,
        comment: values.comment || '',
        dataset_type,
        dataset_format,
        store_format:
          import_type === DATASET_COPY_CHECKER.COPY
            ? DataSourceStructDataType.TFRECORDS
            : store_format,
        import_type: DATASET_COPY_CHECKER.COPY,
        is_published: true,
      } as DatasetCreatePayload),
    );

    if (addDataSetError) {
      setIsDoing(false);
      Message.error(addDataSetError.message);
      return;
    }
    const datasetId = res.data.id;
    const payload: DatasetJobCreatePayload = {
      dataset_job_parameter: {
        dataset_job_kind: finalDataJobType,
        global_configs: {
          [myDomainName]: {
            dataset_uuid: values?.dataset_info?.uuid,
            variables: hydrate(dataJobVariableList, values.params, {
              isStringifyVariableValue: true,
              isStringifyVariableWidgetSchema: true,
              isProcessVariableTypedValue: true,
            }) as DataJobVariable[],
          },
          ...participantList?.reduce(
            (acc, item) => {
              const participantValues = values.participant[item.name];
              acc[item.domain_name] = {
                dataset_uuid: participantValues?.dataset_info?.uuid,
                variables: hydrate(dataJobVariableList, participantValues.params, {
                  isStringifyVariableValue: true,
                  isStringifyVariableWidgetSchema: true,
                  isProcessVariableTypedValue: true,
                }) as DataJobVariable[],
              };

              return acc;
            },
            {} as {
              [domainName: string]: {
                dataset_uuid: ID;
                variables: DataJobVariable[];
              };
            },
          ),
        },
      },
      output_dataset_id: datasetId,
    };

    if (isCron) {
      payload.time_range = {};
      if (cronType === CronType.DAY) {
        payload.time_range.days = 1;
      }
      if (cronType === CronType.HOUR) {
        payload.time_range.hours = 1;
      }
    }

    const [, error] = await to(createDatasetJobs(currentProjectId, payload));
    if (error) {
      Message.error(error.message);
      setIsDoing(false);
      return;
    }

    setIsDoing(false);
    backToList();
  }

  async function onAuthorize() {
    setIsDoing(true);
    const [, error] = await to(authorizeDataset(id));
    if (error) {
      Message.error(error.message);
      setIsDoing(false);
      return;
    }
    setIsDoing(false);
    backToList();
  }
};

export default CreateDataset;
