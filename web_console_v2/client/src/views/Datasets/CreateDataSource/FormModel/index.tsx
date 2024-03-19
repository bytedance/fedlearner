import React, { useState, useMemo } from 'react';
import { Form, Input, Button, Space, Switch, Tag, Popover } from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { validNamePattern, MAX_COMMENT_LENGTH } from 'shared/validator';
import ButtonWithModalConfirm from 'components/ButtonWithModalConfirm';
import { Image, Struct, UnStruct } from 'components/IconPark';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import TitleWithIcon from 'components/TitleWithIcon';
import GridRow from 'components/_base/GridRow';
import BlockRadio from 'components/_base/BlockRadio';
import { DataSourceDataType, DataSourceStructDataType, DatasetType } from 'typings/dataset';
import debounce from 'debounce-promise';
import { checkDataSourceConnection } from 'services/dataset';
import { useGetAppFlagValue, useIsFormValueChange } from 'hooks';
import { FlagKey } from 'typings/flag';

import styled from './index.module.less';

export interface Props<T = any> {
  isEdit: boolean;
  onCancel?: () => void;
  onChange?: (values: T) => void;
  onOk?: (values: T) => Promise<void>;
}

export interface FormData {
  name: string;
  data_source_url: string;
  dataset_format: DataSourceDataType;
  store_format?: DataSourceStructDataType;
  dataset_type: DatasetType;
}

const dataSourceDataTypeAssets = {
  [DataSourceDataType.STRUCT]: { explain: '支持 csv、tfrecords', icon: <Struct /> },
  [DataSourceDataType.NONE_STRUCTURED]: {
    explain: '支持 fastq、bam、vcf、rsa等',
    icon: <UnStruct />,
  },
  [DataSourceDataType.PICTURE]: { explain: '支持 JPEG、PNG、BMP、GIF', icon: <Image /> },
};

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

const FormModal: React.FC<Props<FormData>> = function ({ onCancel, onChange, onOk, isEdit }) {
  const [formInstance] = Form.useForm<any>();
  const [formData, setFormData] = useState<Partial<FormData>>({
    dataset_format: DataSourceDataType.STRUCT,
    store_format: DataSourceStructDataType.CSV,
    dataset_type: DatasetType.PSI,
  });
  const trusted_computing_enabled = useGetAppFlagValue(FlagKey.TRUSTED_COMPUTING_ENABLED);
  const [isCreating, setIsCreating] = useState(false);
  const { isFormValueChanged, onFormValueChange } = useIsFormValueChange(onFormChange);
  const [connectionState, setConnectionState] = useState<'connecting' | 'success' | 'fail'>();
  const [fileNameList, setFileNameList] = useState<string[]>([]);
  const [extraFileCount, setExtraFileCount] = useState<number>(0);

  const dataSourceDataTypeOptions = useMemo(() => {
    const options = [
      {
        value: DataSourceDataType.STRUCT,
        label: '结构化数据',
      },
      {
        value: DataSourceDataType.PICTURE,
        label: '图片',
      },
    ];
    if (trusted_computing_enabled) {
      options.push({
        value: DataSourceDataType.NONE_STRUCTURED,
        label: '非结构化数据',
      });
    }
    return options;
  }, [trusted_computing_enabled]);

  const stateIndicatorProps = useMemo(() => {
    let type: StateTypes = 'processing';
    let text = 'processing';
    switch (connectionState) {
      case 'connecting':
        type = 'processing';
        text = '连接中';
        break;
      case 'success':
        type = 'success';
        text = '连接成功';
        break;
      case 'fail':
        type = 'error';
        text = '连接失败';
        break;
      default:
        break;
    }

    return {
      type,
      text,
    };
  }, [connectionState]);

  const handleCheckDataSource = debounce(async function (value: any, cb) {
    if (isEdit || !formInstance.getFieldValue('data_source_url')) {
      setConnectionState(undefined);
      setFileNameList([]);
      setExtraFileCount(0);
      return;
    }
    setConnectionState('connecting');
    setFileNameList([]);
    setExtraFileCount(0);
    try {
      const resp = await checkDataSourceConnection({
        dataset_type: formInstance.getFieldValue('dataset_type'),
        data_source_url: formInstance.getFieldValue('data_source_url'),
        file_num: 3,
      });
      setFileNameList(resp?.data?.file_names ?? []);
      setExtraFileCount(resp?.data?.extra_nums ?? 0);
      setConnectionState('success');
      typeof cb === 'function' && cb(undefined);
    } catch (error) {
      setConnectionState('fail');
      typeof cb === 'function' && cb(' '); // one space string, validate error but don't show any message
    }
  }, 300);

  return (
    <Form
      className={styled.datas_source_create_form}
      initialValues={formData}
      layout="vertical"
      form={formInstance}
      onSubmit={onSubmit}
      onValuesChange={onFormValueChange}
      scrollToFirstError
    >
      {renderBaseConfigLayout()}
      {renderDataImport()}
      {renderFooterButton()}
    </Form>
  );

  function onSubmit(values: FormData) {
    if (connectionState === 'connecting' || connectionState === 'fail') {
      return;
    }
    setIsCreating(true);
    values.dataset_type = formInstance.getFieldValue('dataset_type');

    if (values.dataset_format !== DataSourceDataType.STRUCT) {
      delete values.store_format;
    }
    onOk?.(values).finally(() => {
      setIsCreating(false);
    });
  }
  function renderBaseConfigLayout() {
    return (
      <section className={styled.data_source_create_section}>
        <h3>基本配置</h3>
        <Form.Item
          field="name"
          label="数据源名称"
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
          <Input.TextArea rows={3} placeholder="最多为 200 个字符" showWordLimit />
        </Form.Item>
        <Form.Item field="dataset_format" label="数据类型" rules={[{ required: true }]}>
          <BlockRadio
            options={dataSourceDataTypeOptions}
            isOneHalfMode={false}
            flexGrow={0}
            blockItemWidth={232}
            renderBlockInner={(item, { label, isActive }) => (
              <GridRow
                style={{
                  height: '55px',
                }}
                gap="10"
              >
                <div className="dataset-type-indicator" data-is-active={isActive}>
                  {dataSourceDataTypeAssets[item.value as DataSourceDataType].icon}
                </div>

                <div>
                  {label}
                  <div className="dataset-type-explain">
                    {dataSourceDataTypeAssets[item.value as DataSourceDataType].explain}
                  </div>
                </div>
              </GridRow>
            )}
          />
        </Form.Item>
        {formData.dataset_format === DataSourceDataType.STRUCT ? (
          <Form.Item
            field="store_format"
            label="数据格式"
            rules={[{ required: true, message: '请选择数据集类型' }]}
          >
            <BlockRadio options={structDataOptions} isOneHalfMode={true} isCenter={true} />
          </Form.Item>
        ) : null}
      </section>
    );
  }

  function renderDataImport() {
    return (
      <section className={styled.data_source_create_section}>
        <h3>数据源导入</h3>
        {formData.dataset_format === DataSourceDataType.STRUCT && (
          <Form.Item field="is_update" label="增量更新">
            <Space>
              <Switch onChange={handleIsUpdateChange} />
              <TitleWithIcon
                title="开启后，将校验数据源路径下子目录数据格式的文件,"
                isLeftIcon={true}
                isShowIcon={true}
                icon={IconInfoCircle}
              />
              <Popover
                trigger="click"
                title="数据源格式要求"
                content={
                  <span className={styled.data_source_is_update_rule}>
                    <p>
                      1.
                      请确认将当前数据路径下包含子文件夹，并且子文件夹以YYYYMMDD（如20201231）或YYYYMMDD-HH（如20201231-12）命名
                    </p>
                    <p>2. 请确认包含 raw_id 列</p>
                  </span>
                }
              >
                <span className={styled.data_source_is_update_text}>查看格式要求</span>
              </Popover>
            </Space>
          </Form.Item>
        )}
        <Form.Item
          style={{ position: 'relative' }}
          hasFeedback
          field="data_source_url"
          label={
            <div className={styled.data_source_url}>
              <span>数据来源</span>
              <StateIndicator
                containerStyle={{
                  position: 'absolute',
                  right: 0,
                  top: 0,
                  visibility: connectionState ? 'visible' : 'hidden',
                }}
                {...stateIndicatorProps}
              />
            </div>
          }
          rules={[
            { required: true, message: '请输入' },
            {
              validator: handleCheckDataSource,
            },
          ]}
        >
          <Input
            placeholder="请填写有效文件目录地址，非文件，如 hdfs:///home/folder"
            onClear={onDataSourceUrlClear}
            allowClear
          />
        </Form.Item>
        <Form.Item field="__file_name_list" label="文件名预览">
          <Space>
            <span className={styled.data_source_form_label}>
              {fileNameList.length > 0 ? fileNameList.join('、') : '暂无数据'}
            </span>
            {Boolean(extraFileCount) && <Tag>+{extraFileCount}</Tag>}
          </Space>
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
        <ButtonWithModalConfirm onClick={onCancel} isShowConfirmModal={isFormValueChanged}>
          取消
        </ButtonWithModalConfirm>
      </Space>
    );
  }
  function handleIsUpdateChange(value: boolean) {
    formInstance.setFieldValue('dataset_type', value ? DatasetType.STREAMING : DatasetType.PSI);
    handleCheckDataSource(value, () => {});
  }
  function onFormChange(_: Partial<FormData>, values: FormData) {
    onChange?.(values);
    setFormData(values);
  }
  function onDataSourceUrlClear() {
    setConnectionState(undefined);
    setFileNameList([]);
    setExtraFileCount(0);
  }
};

export default FormModal;
