import {
  Button,
  Form,
  Input,
  InputNumber,
  Message,
  Space,
  Alert,
  Checkbox,
} from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import FileUpload, { UploadFile, UploadFileType } from 'components/FileUpload';
import { Image, Struct, UnStruct } from 'components/IconPark';
import SharedPageLayout from 'components/SharedPageLayout';
import BlockRadio from 'components/_base/BlockRadio';
import GridRow from 'components/_base/GridRow';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import DataSourceSelect from 'components/DataSourceSelect';
import ConfigForm, { ExposedRef, ItemProps } from 'components/ConfigForm';
import { useQuery } from 'react-query';
import { isEmpty } from 'lodash-es';
import React, { FC, useState, useMemo, useRef } from 'react';
import { useHistory } from 'react-router';
import {
  createDataset,
  createDataSource,
  deleteDataset,
  createDatasetJobs,
  fetchDataJobVariableDetail,
} from 'services/dataset';
import { to, isStringCanBeParsed } from 'shared/helpers';
import { useGetAppFlagValue, useGetCurrentProjectId, useIsFormValueChange } from 'hooks';
import { MAX_COMMENT_LENGTH, validNamePattern } from 'shared/validator';
import { fetchSysInfo } from 'services/settings';
import TitleWithIcon from 'components/TitleWithIcon';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import {
  DataBatchImportPayload,
  DATASET_SCHEMA_CHECKER,
  DatasetCreatePayload,
  DatasetDataType,
  DatasetType__archived,
  DataJobBackEndType,
  DataJobVariable,
  DatasetKindV2,
  DataSourceStructDataType,
  DATASET_COPY_CHECKER,
  DatasetType,
  DataSourceDataType,
  DatasetJobCreatePayload,
} from 'typings/dataset';
import PublishChecker from './PublishChecker';
import { FlagKey } from 'typings/flag';
import DatasetChecker from './DatasetChecker';
import {
  Variable,
  VariableComponent,
  VariableValueType,
  VariableWidgetSchema,
} from 'typings/variable';
import {
  NO_CATEGORY,
  TAG_MAPPER,
  VARIABLE_TIPS_MAPPER,
  CREDITS_LIMITS,
  CronType,
  cronTypeOptions,
} from '../shared';
import { useToggle } from 'react-use';
import { Tag as TagEnum } from 'typings/workflow';
import { hydrate } from 'views/Workflows/shared';
import './index.less';

type Props = Record<string, unknown>;

enum DataImportWay {
  Remote = 'remote',
  Local = 'local',
}
type Params = {
  [key: string]: any;
};
type FormData = DatasetCreatePayload &
  DataBatchImportPayload & {
    _import_from: DataImportWay;
    data_format: DatasetDataType;
    files?: UploadFile[];
    params: Params;
    data_source_uuid: ID;
    store_format: DataSourceStructDataType;
    import_type: DATASET_COPY_CHECKER;
    cron_type: CronType;
  };

const newDatasetTypeOptions = [
  {
    value: DatasetDataType.STRUCT,
    label: '结构化数据',
  },
  {
    value: DatasetDataType.PICTURE,
    label: '图片',
  },
  // {
  //   value: DatasetDataType.UNSTRUCT,
  //   label: '非结构化数据',
  // },
];

const importWayOptions = [
  {
    value: DataImportWay.Remote,
    label: '数据源导入',
  },
  {
    value: DataImportWay.Local,
    label: '本地导入',
  },
];

const structDataOptions = [
  {
    value: DataSourceStructDataType.CSV,
    label: 'csv',
  },
  {
    value: DataSourceStructDataType.TFRECORDS,
    label: 'tfrecords',
  },
];

const datasetTypeAssets = {
  [DatasetDataType.STRUCT]: { explain: '支持csv、tfrecord', icon: <Struct /> },
  [DatasetDataType.PICTURE]: { explain: '支持JPEG、PNG、BMP、GIF', icon: <Image /> },
  [DatasetDataType.NONE_STRUCTURED]: { explain: '支持 fastq、bam、vcf、rsa等', icon: <UnStruct /> },
};

const CreateDataset: FC<Props> = () => {
  const [formInstance] = Form.useForm<FormData>();
  const history = useHistory();

  const currentProjectId = useGetCurrentProjectId();

  const dataJobVariableDetailQuery = useQuery(
    ['getDataJobVariableDetail', DataJobBackEndType.IMPORT_SOURCE],
    () => fetchDataJobVariableDetail(DataJobBackEndType.IMPORT_SOURCE),
    {
      enabled: true,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const [formData, setFormData] = useState<Partial<FormData>>({
    project_id: currentProjectId,
    dataset_type: DatasetType__archived.PSI,
    store_format: DataSourceStructDataType.CSV,
    data_format: DatasetDataType.STRUCT,
    _import_from: DataImportWay.Remote,
    need_publish: false,
    value: 100,
    schema_checkers: [DATASET_SCHEMA_CHECKER.RAW_ID_CHECKER],
    cron_type: CronType.DAY,
  });

  const [isCreating, setIsCreating] = useState(false);
  const [needPublish, setNeedPublish] = useState(false);
  const [copyState, setCopyState] = useState({
    isShow: true,
    isDisabled: false,
    isCopy: true,
  });
  const [isShowCron, toggleShowCron] = useToggle(false);
  const [cronType, setCornType] = useState<CronType>(CronType.DAY);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);
  const bcs_support_enabled = useGetAppFlagValue(FlagKey.BCS_SUPPORT_ENABLED);
  const configFormRefList = useRef<Array<ExposedRef | null>>([]);

  const sysInfoQuery = useQuery(['getSysInfo'], () => fetchSysInfo(), {
    retry: 2,
    refetchOnWindowFocus: false,
  });

  const myDomainName = useMemo<string>(() => {
    return sysInfoQuery.data?.data?.domain_name ?? '';
  }, [sysInfoQuery.data]);

  const dataJobVariableList = useMemo<Variable[]>(() => {
    if (!dataJobVariableDetailQuery.data?.data?.variables) {
      return [];
    }

    return dataJobVariableDetailQuery.data.data.variables.map((item) => {
      let widget_schema: VariableWidgetSchema = {};

      try {
        widget_schema = JSON.parse(item.widget_schema);
      } catch (error) {}

      return {
        ...item,
        widget_schema,
      };
    });
  }, [dataJobVariableDetailQuery.data]);

  const paramsList = useMemo<ItemProps[]>(() => {
    const list: ItemProps[] = [];
    dataJobVariableList
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

        list.push({
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
                    validator: (value, callback) => {
                      if ((value && typeof value === 'object') || isStringCanBeParsed(value)) {
                        callback();
                        return;
                      }
                      callback(`JSON ${item.value_type!} 格式错误`);
                    },
                  },
                ]
              : baseRuleList,
        });
      });
    return list;
  }, [dataJobVariableList]);

  return (
    <SharedPageLayout
      title={
        <BackButton onClick={backToList} isShowConfirmModal={isFormValueChanged}>
          原始数据集
        </BackButton>
      }
      centerTitle="创建数据集"
    >
      <Form
        className="dataset-raw-create-form"
        initialValues={formData}
        layout="vertical"
        form={formInstance}
        onSubmit={onSubmit}
        onValuesChange={onFormValueChange}
        scrollToFirstError
      >
        {renderBaseConfigLayout()}
        {formData._import_from === DataImportWay.Remote && renderDataSourceImportLayout()}
        {formData._import_from === DataImportWay.Local && renderLocalImportLayout()}
        {formData.data_format === DatasetDataType.STRUCT && renderDatasetChecker()}
        {renderParamsConfig()}
        {renderPublishChecker()}
        {needPublish && bcs_support_enabled && renderCreditsInput()}
        {renderFooterButton()}
      </Form>
    </SharedPageLayout>
  );

  function renderBaseConfigLayout() {
    return (
      <section className="form-section">
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
          label="描述"
          rules={[{ maxLength: MAX_COMMENT_LENGTH, message: '最多为 200 个字符' }]}
        >
          <Input.TextArea rows={2} placeholder="最多为 200 个字符" showWordLimit />
        </Form.Item>
        <Form.Item
          field="_import_from"
          label="导入方式"
          rules={[{ required: true, message: '请选择数据集类型' }]}
        >
          <BlockRadio
            options={importWayOptions}
            isOneHalfMode={true}
            isCenter={true}
            onChange={handleImportTypeChange}
          />
        </Form.Item>
      </section>
    );
  }

  function renderDataSourceImportLayout() {
    return (
      <section className="form-section">
        <h3>数据源导入</h3>
        <Form.Item
          field="data_source_uuid"
          label="数据源"
          rules={[{ required: true, message: '请选择' }]}
        >
          <DataSourceSelect valueKey="uuid" onChange={handleDataSourceChange} />
        </Form.Item>
        {isShowCron && (
          <Form.Item field="cron_type" label="导入周期">
            <BlockRadio
              flexGrow={0}
              isCenter={false}
              isWarnTip={true}
              gap={10}
              isOneHalfMode={false}
              options={cronTypeOptions}
              onChange={(val: CronType) => {
                setCornType(val);
              }}
            />
          </Form.Item>
        )}

        {copyState.isShow && (
          <Form.Item field="import_type" label="数据配置">
            <Space size="large">
              <Checkbox
                checked={copyState.isCopy}
                disabled={copyState.isDisabled}
                onChange={handleChangeIsCopy}
              >
                {
                  <TitleWithIcon
                    isShowIcon={true}
                    isBlock={false}
                    title="数据拷贝"
                    icon={IconInfoCircle}
                    tip="开启后，数据信息将拷贝至平台对应的数据库存储中，以便后续训练。当数据集用于可信计算,或定时求交数据量过大(例如天级求交存量数据大于15天)时,建议关闭该选项。"
                  />
                }
              </Checkbox>
            </Space>
          </Form.Item>
        )}
      </section>
    );
  }
  function renderLocalImportLayout() {
    return (
      <section className="form-section">
        <h3>本地导入</h3>
        <Form.Item field="data_format" label="数据类型" rules={[{ required: true }]}>
          <BlockRadio
            options={newDatasetTypeOptions}
            isOneHalfMode={false}
            flexGrow={0}
            blockItemWidth={232}
            renderBlockInner={(item, { label, isActive }) => (
              <GridRow
                style={{
                  height: '52px',
                }}
                gap="10"
              >
                <div className="dataset-type-indicator" data-is-active={isActive}>
                  {datasetTypeAssets[item.value as DatasetDataType].icon}
                </div>

                <div>
                  {label}
                  <div className="dataset-type-explain">
                    {datasetTypeAssets[item.value as DatasetDataType].explain}
                  </div>
                </div>
              </GridRow>
            )}
          />
        </Form.Item>
        {formData.data_format === DatasetDataType.STRUCT && (
          <Form.Item
            field="store_format"
            label="数据格式"
            rules={[{ required: true, message: '请选择数据集类型' }]}
          >
            <BlockRadio options={structDataOptions} isOneHalfMode={true} isCenter={true} />
          </Form.Item>
        )}

        <Form.Item
          field="files"
          label="从本地文件中选择"
          rules={[{ required: true, message: '请上传文件' }]}
        >
          <FileUpload
            accept={
              formData.data_format === DatasetDataType.STRUCT ? '.csv,.tfrecords' : '.tar,.gz'
            }
            data={
              formData.data_format === DatasetDataType.STRUCT
                ? {
                    extract: false,
                    kind: UploadFileType.Dataset,
                  }
                : {
                    extract: true,
                    kind: UploadFileType.Dataset,
                  }
            }
            kind={UploadFileType.Dataset}
            maxCount={1}
            maxSize={1024 * 1024 * 100} // 100MB
            dp={0}
          />
        </Form.Item>
      </section>
    );
  }

  function renderDatasetChecker() {
    return (
      <section className="form-section">
        <h3>数据校验</h3>
        <Form.Item field="schema_checkers">
          <DatasetChecker />
        </Form.Item>
      </section>
    );
  }
  function renderFooterButton() {
    return (
      <Space>
        <Button type="primary" htmlType="submit" loading={isCreating}>
          确认创建
        </Button>
        <ButtonWithModalConfirm onClick={backToList} isShowConfirmModal={isFormValueChanged}>
          取消
        </ButtonWithModalConfirm>
      </Space>
    );
  }

  function renderParamsConfig() {
    return (
      <Space>
        <Form.Item field="params">
          {dataJobVariableDetailQuery.isError ? (
            <Alert type="info" content="暂不支持该类型的数据任务" />
          ) : (
            <ConfigForm
              filter={variableTagFilter}
              groupBy={'tag'}
              hiddenGroupTag={false}
              cols={2}
              collapseTitle="参数配置"
              collapseFormItemList={paramsList}
              ref={(ref) => {
                configFormRefList.current[0] = ref;
              }}
              isResetOnFormItemListChange={true}
            />
          )}
        </Form.Item>
      </Space>
    );
  }

  function renderPublishChecker() {
    return (
      <Form.Item field="need_publish">
        <PublishChecker onChange={setNeedPublish} />
      </Form.Item>
    );
  }

  function renderCreditsInput() {
    return (
      <Form.Item labelAlign="left" layout="horizontal" label="使用单价" field="value">
        <InputNumber
          className="dataset-raw-input-number"
          min={CREDITS_LIMITS.MIN}
          max={CREDITS_LIMITS.MAX}
          suffix="积分"
          step={1}
        />
      </Form.Item>
    );
  }

  function variableTagFilter(item: ItemProps) {
    return (
      !!item.tag &&
      [TAG_MAPPER[TagEnum.INPUT_PARAM], TAG_MAPPER[TagEnum.RESOURCE_ALLOCATION]].includes(item.tag)
    );
  }

  function handleDataSourceChange(id: string, options: any) {
    const dataSource = options ? options.extra : {};
    const isStreaming = dataSource.dataset_type === DatasetType__archived.STREAMING;
    formInstance.setFieldsValue({
      data_format: dataSource.dataset_format,
      store_format: dataSource.store_format,
      dataset_type: dataSource.dataset_type,
      cron_type: CronType.DAY,
    });
    toggleShowCron(isStreaming);
    setCornType(CronType.DAY);
    switch (dataSource.dataset_format) {
      case DatasetDataType.STRUCT:
        // 结构化数据， 只有TFRECORDS格式支持，非拷贝
        setCopyState({
          isShow: dataSource.store_format === DataSourceStructDataType.TFRECORDS,
          isDisabled: false,
          isCopy: true,
        });
        break;
      case DatasetDataType.PICTURE:
        setCopyState({
          isShow: false,
          isDisabled: false,
          isCopy: true,
        });
        break;
      case DatasetDataType.NONE_STRUCTURED:
        setCopyState({
          isShow: true,
          isDisabled: true,
          isCopy: false,
        });
        break;
      default:
        setCopyState({
          isShow: true,
          isDisabled: false,
          isCopy: true,
        });
        break;
    }
  }

  function handleImportTypeChange() {
    formInstance.resetFields(['data_source_uuid', 'data_format', 'store_format', 'dataset_type']);
    setCopyState({
      isShow: true,
      isDisabled: false,
      isCopy: true,
    });
  }

  function backToList() {
    history.goBack();
  }

  function handleChangeIsCopy(val: boolean) {
    setCopyState({
      ...copyState,
      isCopy: val,
    });
  }

  async function onSubmit() {
    if (!currentProjectId) {
      return Message.error('请选择工作区');
    }

    if (!myDomainName) {
      return Message.error('获取本系统 domain_name 失败');
    }

    const { _import_from } = formInstance.getFieldsValue();
    const import_type = copyState.isCopy
      ? DATASET_COPY_CHECKER.COPY
      : DATASET_COPY_CHECKER.NONE_COPY;
    // validate params
    const files = (formInstance.getFieldValue('files') as any) as UploadFile[];

    if (_import_from === DataImportWay.Local && isEmpty(files)) {
      return Message.error('请选择需要导入的文件');
    }

    setIsCreating(true);

    let dataSourceUuid: ID = formInstance.getFieldValue('data_source_uuid') as ID;
    if (_import_from === DataImportWay.Local) {
      const data_format = formInstance.getFieldValue('data_format');
      const [dataSourceResp, createDataSourceError] = await to(
        createDataSource({
          project_id: currentProjectId!,
          data_source: {
            // TODO: name
            name: files?.[0]?.internal_directory,
            data_source_url: files?.[0]?.internal_directory,
            is_user_upload: true,
            store_format:
              data_format === DatasetDataType.STRUCT
                ? (formInstance.getFieldValue('store_format') as DataSourceStructDataType)
                : undefined,
            dataset_type: formInstance.getFieldValue('dataset_type') as DatasetType,
            dataset_format: formInstance.getFieldValue('data_format') as DataSourceDataType,
          },
        }),
      );

      if (createDataSourceError) {
        setIsCreating(false);
        Message.error(createDataSourceError.message);
        return;
      }

      dataSourceUuid = dataSourceResp.data.uuid;
    }

    let store_format = formInstance.getFieldValue('store_format');
    // 对于非拷贝及本地导入， 存储格式一定为TFRECORDS
    if (import_type === DATASET_COPY_CHECKER.COPY || _import_from === DataImportWay.Local) {
      store_format = DataSourceStructDataType.TFRECORDS;
    }

    // create dataset
    const [res, error] = await to(
      createDataset({
        kind: DatasetKindV2.RAW,
        project_id: currentProjectId,
        name: formInstance.getFieldValue('name'),
        comment: formInstance.getFieldValue('comment'),
        dataset_type: formInstance.getFieldValue('dataset_type'),
        dataset_format: formInstance.getFieldValue('data_format'),
        store_format,
        import_type,
        need_publish: formInstance.getFieldValue('need_publish'),
        value:
          !!formInstance.getFieldValue('need_publish') && !!bcs_support_enabled
            ? formInstance.getFieldValue('value')
            : undefined,
        schema_checkers:
          formData.data_format === DatasetDataType.PICTURE
            ? []
            : formInstance.getFieldValue('schema_checkers'),
      } as DatasetCreatePayload),
    );
    if (error) {
      setIsCreating(false);
      Message.error(error.message);
      return;
    }
    const datasetId = res.data.id;

    const payload: DatasetJobCreatePayload = {
      dataset_job_parameter: {
        dataset_job_kind: DataJobBackEndType.IMPORT_SOURCE,
        global_configs: {
          [myDomainName]: {
            dataset_uuid: dataSourceUuid,
            variables: hydrate(
              dataJobVariableList,
              formInstance.getFieldValue('params') as Params,
              {
                isStringifyVariableValue: true,
                isStringifyVariableWidgetSchema: true,
                isProcessVariableTypedValue: true,
              },
            ) as DataJobVariable[],
          },
        },
      },
      output_dataset_id: datasetId,
    };
    // 对于增量数据集， 原始数据集需要传入定时周期
    if (isShowCron) {
      payload.time_range = {};
      if (cronType === CronType.DAY) {
        payload.time_range.days = 1;
      }
      if (cronType === CronType.HOUR) {
        payload.time_range.hours = 1;
      }
    }

    const [, addDatasetJobError] = await to(createDatasetJobs(currentProjectId, payload));
    if (addDatasetJobError) {
      Message.error(addDatasetJobError.message);
      // TODO: what if delete request also failed?
      try {
        deleteDataset(datasetId);
      } catch {
        /** ignore error */
      }
      setIsCreating(false);
      return;
    }

    setIsCreating(false);

    Message.success(needPublish ? '创建成功，数据集可用后将自动发布' : '创建成功');

    history.goBack();
  }
  function onFormChange(_: Partial<FormData>, values: FormData) {
    setFormData(values);
  }
};

export default CreateDataset;
