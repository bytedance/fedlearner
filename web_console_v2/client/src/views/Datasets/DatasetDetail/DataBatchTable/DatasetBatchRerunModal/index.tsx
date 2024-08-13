import React, { FC, useState, useEffect } from 'react';
import { to, isStringCanBeParsed } from 'shared/helpers';
import { rerunDatasetBatchById } from 'services/dataset';
import { Modal, Form, Input, Message } from '@arco-design/web-react';
import { DataJobVariable, GlobalConfigs, DataJobBackEndType } from 'typings/dataset';
import {
  Variable,
  VariableComponent,
  VariableValueType,
  VariableWidgetSchema,
} from 'typings/variable';
import ConfigForm, { ItemProps } from 'components/ConfigForm';
import {
  TAG_MAPPER,
  VARIABLE_TIPS_MAPPER,
  NO_CATEGORY,
  SYNCHRONIZATION_VARIABLE,
  isSingleParams,
} from '../../../shared';
import { Tag as TagEnum } from 'typings/workflow';
import {
  useGetCurrentProjectParticipantList,
  useGetCurrentPureDomainName,
  useGetCurrentDomainName,
} from 'hooks';
import { hydrate } from 'views/Workflows/shared';
import styled from './index.module.less';

export interface Props {
  visible: boolean;
  id: ID;
  batchId: ID;
  batchName: string;
  kind: DataJobBackEndType;
  globalConfigs: GlobalConfigs;
  onSuccess?: () => void;
  onFail?: () => void;
  onCancel?: () => void;
}

type Params = {
  [key: string]: any;
};
type FormData = {
  batch_name: string;
  params: Params;
  participant: {
    [participantName: string]: {
      params: Params;
    };
  };
};

const DatasetBatchRerunModal: FC<Props> = ({
  id,
  batchId,
  batchName,
  kind,
  visible,
  globalConfigs,
  onSuccess,
  onFail,
  onCancel,
}) => {
  const participantList = useGetCurrentProjectParticipantList();
  const myPureDomainName = useGetCurrentPureDomainName();
  const myDomainName = useGetCurrentDomainName();
  const [globalConfigMap, setGlobalConfigMap] = useState<any>({});

  const [formInstance] = Form.useForm<FormData>();
  const isSingle = isSingleParams(kind);
  useEffect(() => {
    const globalConfigParseMap: any = {};
    Object.keys(globalConfigs).forEach((key) => {
      const globalConfig = globalConfigs[key];
      globalConfigParseMap[key] = handleParseToConfigFrom(
        handleParseDefinition(globalConfig.variables),
        false,
      );
    });
    setGlobalConfigMap(globalConfigParseMap);
  }, [globalConfigs, batchId]);

  useEffect(() => {
    formInstance.setFieldValue('batch_name', batchName);
  }, [batchName, formInstance]);
  return (
    <Modal
      title="重新运行"
      visible={visible}
      maskClosable={false}
      afterClose={afterClose}
      onCancel={onCancel}
      onOk={handleOnOk}
      // footer={null}
      className={styled.model}
    >
      <Form form={formInstance} onSubmit={onSubmit}>
        <Form.Item field="batch_name" label="数据集批次" disabled={true}>
          <Input />
        </Form.Item>
        <Form.Item label="我方参数" field="params">
          <ConfigForm
            filter={variableTagFilter}
            groupBy={'tag'}
            hiddenGroupTag={true}
            hiddenCollapse={true}
            cols={2}
            formItemList={globalConfigMap[myPureDomainName]}
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
        </Form.Item>
        {!isSingle && renderParticipantConfigLayout()}
      </Form>
    </Modal>
  );
  function renderParticipantConfigLayout() {
    return participantList?.map((item, index) => {
      const { pure_domain_name } = item;
      return (
        <Form.Item field={`participant.${item.name}.params`} label={`${item.name}参数`} key={index}>
          <ConfigForm
            filter={variableTagFilter}
            groupBy={'tag'}
            hiddenGroupTag={true}
            hiddenCollapse={true}
            cols={2}
            formItemList={globalConfigMap[pure_domain_name!]}
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
        </Form.Item>
      );
    });
  }
  function variableTagFilter(item: ItemProps) {
    return !!item.tag && [TAG_MAPPER[TagEnum.RESOURCE_ALLOCATION]].includes(item.tag);
  }

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
    return variableList
      .filter((item) => !item.widget_schema.hidden)
      .map((item) => {
        const baseRuleList = item.widget_schema.required
          ? [
              {
                required: true,
                message: '必填项',
              },
            ]
          : [];
        return {
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
      });
  }

  async function onSubmit(values: FormData) {
    if (!formInstance) {
      return;
    }
    const participantParams: {
      [domainName: string]: {
        dataset_uuid: ID;
        variables: DataJobVariable[];
      };
    } = {};

    if (!isSingle) {
      participantList?.reduce(
        (acc, item) => {
          const participantValues = values.participant[item.name];
          acc[item.domain_name] = {
            dataset_uuid: globalConfigs[item.pure_domain_name!]?.dataset_uuid,
            variables: hydrate(
              globalConfigs[item.pure_domain_name!]?.variables,
              participantValues.params,
              {
                isStringifyVariableValue: true,
                isStringifyVariableWidgetSchema: true,
                isProcessVariableTypedValue: true,
              },
            ) as DataJobVariable[],
          };

          return acc;
        },
        {} as {
          [domainName: string]: {
            dataset_uuid: ID;
            variables: DataJobVariable[];
          };
        },
      );
    }

    const [, err] = await to(
      rerunDatasetBatchById(id!, batchId!, {
        dataset_job_parameter: {
          global_configs: {
            [myDomainName]: {
              dataset_uuid: globalConfigs[myPureDomainName].dataset_uuid,
              variables: hydrate(globalConfigs[myPureDomainName].variables, values.params, {
                isStringifyVariableValue: true,
                isStringifyVariableWidgetSchema: true,
                isProcessVariableTypedValue: true,
              }) as DataJobVariable[],
            },
            ...participantParams,
          },
        },
      }),
    );
    if (err) {
      onFail?.();
      Message.error(err.message || '重新运行失败');
      return;
    }

    Message.success('重新运行成功');
    onSuccess?.();
  }

  function handleOnOk() {
    formInstance.submit();
  }

  function afterClose() {
    // Clear all fields
    formInstance.resetFields();
  }
};

export default DatasetBatchRerunModal;
