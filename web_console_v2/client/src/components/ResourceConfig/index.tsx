/* istanbul ignore file */

import React, { FC, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import i18n from 'i18n';

import { convertCpuCoreToM } from 'shared/helpers';

import { Form, Collapse } from '@arco-design/web-react';
import InputGroup, { TColumn } from 'components/InputGroup';
import BlockRadio from 'components/_base/BlockRadio';

import { ResourceTemplateType, AlgorithmType } from 'typings/modelCenter';
import { EnumAlgorithmProjectType } from 'typings/algorithm';

const StyledCollapse = styled(Collapse)`
  overflow: initial;
  .arco-collapse-item-header {
    position: relative;
    left: -14px;
    border-width: 0;
    &-title {
      font-weight: 400 !important;
      font-size: 12px;
    }
  }
  .arco-collapse-item-content {
    background-color: transparent;
  }
  .arco-collapse-item-content-box {
    padding: 0;
  }
`;

const RESOURCE_HIGH_TREE = {
  master_replicas: 1,
  master_cpu: 0,
  master_mem: 0,
  ps_replicas: 1,
  ps_cpu: 0,
  ps_mem: 0,
  worker_replicas: 1,
  worker_cpu: 16,
  worker_mem: 64,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_HIGH_NN = {
  master_replicas: 1,
  master_cpu: 2,
  master_mem: 32,
  ps_replicas: 1,
  ps_cpu: 8,
  ps_mem: 32,
  worker_replicas: 1,
  worker_cpu: 8,
  worker_mem: 32,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_MEDIUM_TREE = {
  master_replicas: 1,
  master_cpu: 0,
  master_mem: 0,
  ps_replicas: 1,
  ps_cpu: 0,
  ps_mem: 0,
  worker_replicas: 1,
  worker_cpu: 8,
  worker_mem: 32,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_MEDIUM_NN = {
  master_replicas: 1,
  master_cpu: 1,
  master_mem: 16,
  ps_replicas: 1,
  ps_cpu: 4,
  ps_mem: 16,
  worker_replicas: 1,
  worker_cpu: 4,
  worker_mem: 16,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_LOW_TREE = {
  master_replicas: 1,
  master_cpu: 0,
  master_mem: 0,
  ps_replicas: 1,
  ps_cpu: 0,
  ps_mem: 0,
  worker_replicas: 1,
  worker_cpu: 4,
  worker_mem: 8,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_LOW_NN = {
  master_replicas: 1,
  master_cpu: 1,
  master_mem: 4,
  ps_replicas: 1,
  ps_cpu: 2,
  ps_mem: 4,
  worker_replicas: 1,
  worker_cpu: 2,
  worker_mem: 4,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};
const RESOURCE_CUSTOM_NN = {
  master_replicas: 1,
  master_cpu: 1,
  master_mem: 4,
  ps_replicas: 1,
  ps_cpu: 2,
  ps_mem: 4,
  worker_replicas: 1,
  worker_cpu: 4,
  worker_mem: 8,
  worker_roles: 'worker',
  ps_roles: 'ps',
  master_roles: 'master',
};

enum TResourceFieldType {
  MASTER = 'master',
  PS = 'ps',
  WORKER = 'worker',
}
type TResource = typeof RESOURCE_LOW_NN;

const roleFieldList = [TResourceFieldType.MASTER, TResourceFieldType.PS, TResourceFieldType.WORKER];
const resourceFieldList = ['replicas', 'cpu', 'mem'];

export const classifyResourceWithTemplateType = (resource: Partial<TResource>) => {
  const ret: Record<string, [Partial<Record<keyof TResource, number | string>>]> = {};
  for (const key in resource) {
    const [type] = key.split('_');
    if (!ret[type]) {
      ret[type] = [{}];
    }
    ret[type][0][key as keyof TResource] = resource[key as keyof TResource];
  }
  return ret;
};

export const unwrapResourceFromTemplateType = (payload: Record<string, any>) => {
  const copied = { ...payload };
  for (const key in copied) {
    if (
      [TResourceFieldType.MASTER, TResourceFieldType.PS, TResourceFieldType.WORKER].includes(
        key as TResourceFieldType,
      ) === false
    ) {
      continue;
    }

    const [resource] = copied[key];

    for (const k in resource) {
      const [, resType] = k.split('_');
      let unit = '';
      let value = resource[k];

      switch (resType as TResourceType) {
        case 'cpu':
          unit = 'm';
          value = convertCpuCoreToM(value, false);
          break;
        case 'mem':
          unit = 'Gi';
          break;
      }
      copied[k] = value + unit;
    }
    delete copied[key];
  }
  return copied;
};

export const wrapResource = (formValue: Record<string, any>) => {
  const classifiedFormValue = classifyResourceWithTemplateType(formValue);

  const tempObj: any = {};

  roleFieldList.forEach((role) => {
    if (!classifiedFormValue[role] || !classifiedFormValue[role][0]) return;
    const tempFormValue = classifiedFormValue[role][0] as any;

    Object.keys(tempFormValue).forEach((key) => {
      const [role, field] = key.split('_');
      if (resourceFieldList.includes(field)) {
        if (!tempObj[role]) {
          tempObj[role] = [
            {
              [`${role}_roles`]: role,
            },
          ];
        }

        if (field === 'cpu') {
          // convert cpu unit, m to Core
          tempObj[role][0][key] = parseFloat(tempFormValue[key]) / 1000;
        } else {
          tempObj[role][0][key] = parseInt(tempFormValue[key]);
        }
      }
    });
  });

  return { ...formValue, ...tempObj };
};

export const resourceTemplateParamsMap = {
  [ResourceTemplateType.HIGH]: {
    [EnumAlgorithmProjectType.TREE_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_HIGH_TREE),
    [EnumAlgorithmProjectType.TREE_HORIZONTAL]: classifyResourceWithTemplateType(
      RESOURCE_HIGH_TREE,
    ),
    [EnumAlgorithmProjectType.NN_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_HIGH_NN),
    [EnumAlgorithmProjectType.NN_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_HIGH_NN),
  },
  [ResourceTemplateType.MEDIUM]: {
    [EnumAlgorithmProjectType.TREE_VERTICAL]: classifyResourceWithTemplateType(
      RESOURCE_MEDIUM_TREE,
    ),
    [EnumAlgorithmProjectType.TREE_HORIZONTAL]: classifyResourceWithTemplateType(
      RESOURCE_MEDIUM_TREE,
    ),
    [EnumAlgorithmProjectType.NN_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_MEDIUM_NN),
    [EnumAlgorithmProjectType.NN_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_MEDIUM_NN),
  },
  [ResourceTemplateType.LOW]: {
    [EnumAlgorithmProjectType.TREE_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_LOW_TREE),
    [EnumAlgorithmProjectType.TREE_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_LOW_TREE),
    [EnumAlgorithmProjectType.NN_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_LOW_NN),
    [EnumAlgorithmProjectType.NN_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_LOW_NN),
  },
  [ResourceTemplateType.CUSTOM]: {
    [EnumAlgorithmProjectType.TREE_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_LOW_TREE),
    [EnumAlgorithmProjectType.TREE_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_LOW_TREE),
    [EnumAlgorithmProjectType.NN_VERTICAL]: classifyResourceWithTemplateType(RESOURCE_CUSTOM_NN),
    [EnumAlgorithmProjectType.NN_HORIZONTAL]: classifyResourceWithTemplateType(RESOURCE_CUSTOM_NN),
  },
};

export const resourceTemplateTypeOptions = [
  {
    value: ResourceTemplateType.HIGH,
    label: i18n.t('model_center.label_radio_high'),
  },
  {
    value: ResourceTemplateType.MEDIUM,
    label: i18n.t('model_center.label_radio_medium'),
  },
  {
    value: ResourceTemplateType.LOW,
    label: i18n.t('model_center.label_radio_low'),
  },
  {
    value: ResourceTemplateType.CUSTOM,
    label: i18n.t('model_center.label_radio_custom'),
  },
];

type TResourceType = 'cpu' | 'mem' | 'replicas' | undefined;
const getAlgorithmColumns = (
  roleType: TResourceFieldType,
  columnTypes: [TResourceType, TResourceType, TResourceType],
  disabled = false,
  localDisabledList: string[] = [],
): TColumn[] => {
  const type = 'INPUT_NUMBER';
  const columnsMap: Record<string, TColumn> = {
    cpu: {
      type,
      dataIndex: `${roleType}_cpu`,
      title: i18n.t('cpu'),
      unitLabel: 'Core',
      placeholder: i18n.t('placeholder_cpu'),
      rules: [{ required: true, message: i18n.t('model_center.msg_required') }],
      span: 0,
      min: 0.1,
      tooltip: i18n.t('tip_please_input_positive_number'),
      precision: 1,
      disabled: disabled || !!localDisabledList.find((item: string) => item === `${roleType}.cpu`),
    },
    replicas: {
      type,
      dataIndex: `${roleType}_replicas`,
      title: i18n.t('replicas'),
      placeholder: i18n.t('placeholder_input'),
      min: 1,
      max: 100,
      precision: 0,
      rules: [
        { required: true, message: i18n.t('model_center.msg_required') },
        { min: 1, type: 'number' },
        { max: 100, type: 'number' },
      ],
      span: 0,
      tooltip: i18n.t('tip_replicas_range'),
      mode: 'button',
      disabled:
        disabled || !!localDisabledList.find((item: string) => item === `${roleType}.replicas`),
    },
    mem: {
      type,
      dataIndex: `${roleType}_mem`,
      title: i18n.t('mem'),
      unitLabel: 'Gi',
      placeholder: i18n.t('placeholder_mem'),
      rules: [{ required: true, message: i18n.t('model_center.msg_required') }],
      span: 0,
      min: 1,
      tooltip: i18n.t('tip_please_input_positive_integer'),
      disabled: disabled || !!localDisabledList.find((item: string) => item === `${roleType}.mem`),
    },
  };

  const ret: TColumn[] = [
    {
      type: 'TEXT',
      dataIndex: `${roleType}_roles`,
      title: 'roles',
      span: 0,
      disabled: true,
    },
  ];
  for (const type of columnTypes) {
    if (type) {
      ret.push(columnsMap[type]);
    }
  }

  return ret.map((col) => ({
    ...col,
    span: Math.floor(24 / ret.length),
  }));
};

export type MixedAlgorithmType =
  | EnumAlgorithmProjectType.TREE_VERTICAL
  | EnumAlgorithmProjectType.TREE_HORIZONTAL
  | EnumAlgorithmProjectType.NN_VERTICAL
  | EnumAlgorithmProjectType.NN_HORIZONTAL
  | AlgorithmType.TREE
  | AlgorithmType.NN;

export type Value = {
  resource_type: ResourceTemplateType | `${ResourceTemplateType}`;

  master_cpu?: string;
  master_mem?: string;
  master_replicas?: string;

  ps_cpu?: string;
  ps_mem?: string;
  ps_replicas?: string;

  worker_cpu?: string;
  worker_mem?: string;
  worker_replicas?: string;
};

export type Props = {
  value?: Value;
  onChange?: (value: Value) => void;
  disabled?: boolean;
  localDisabledList?: string[];
  defaultResourceType?: ResourceTemplateType | `${ResourceTemplateType}`;
  algorithmType?: MixedAlgorithmType;
  collapsedTitle?: string;
  isIgnoreFirstRender?: boolean;
  isTrustedCenter?: boolean;
  collapsedOpen?: boolean;
};

const formLayout = {
  labelCol: {
    span: 0,
  },
  wrapperCol: {
    span: 24,
  },
};

export const ResourceConfig: FC<Props> = ({
  disabled: disabledFromProps = false,
  localDisabledList = [],
  defaultResourceType = ResourceTemplateType.LOW,
  algorithmType = EnumAlgorithmProjectType.TREE_VERTICAL,
  collapsedTitle = i18n.t('model_center.title_resource_config_detail'),
  isIgnoreFirstRender = true,
  isTrustedCenter = false,
  collapsedOpen = true,
  value,
  onChange,
}) => {
  const isControlled = typeof value === 'object' && value !== null;
  const [form] = Form.useForm();

  const [collapseActiveKey, setCollapseActiveKey] = useState<string[]>(collapsedOpen ? ['1'] : []); // default open status controlled by 'collapsedOpen'
  const [resourceType, setResourceType] = useState(() => {
    if (isControlled) {
      return value?.resource_type;
    }

    return defaultResourceType || ResourceTemplateType.LOW;
  });
  const isAlreadyClickResource = useRef(false);

  useEffect(() => {
    if (isControlled) {
      form.setFieldsValue(wrapResource({ ...value }));
    }
  }, [form, isControlled, value]);

  useEffect(() => {
    if (resourceType && algorithmType) {
      const innerValue = {
        ...(resourceTemplateParamsMap[resourceType] as any)[algorithmType],
      };
      const finaleValue = {
        resource_type: resourceType,
        ...unwrapResourceFromTemplateType(innerValue),
      };
      if (!isControlled) {
        form.setFieldsValue(innerValue);
        onChange?.(finaleValue as any);
      }
      if (isControlled) {
        // Ignore first render
        if (isIgnoreFirstRender && isAlreadyClickResource.current) {
          onChange?.(finaleValue as any);
        }
        if (!isIgnoreFirstRender) {
          onChange?.(finaleValue as any);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form, resourceType, algorithmType, isControlled, isIgnoreFirstRender]);

  const disabled = resourceType !== ResourceTemplateType.CUSTOM || disabledFromProps;

  return (
    <Form
      form={form}
      {...formLayout}
      initialValues={{
        resource_type: resourceType,
      }}
      onChange={(_, values) => {
        const finaleValue = unwrapResourceFromTemplateType(values);
        onChange?.(finaleValue as any);
      }}
    >
      <Form.Item field="resource_type">
        <BlockRadio
          isCenter={true}
          options={resourceTemplateTypeOptions}
          disabled={disabledFromProps}
          onChange={(value: ResourceTemplateType) => {
            isAlreadyClickResource.current = true;
            setResourceType(value);
            if (value === ResourceTemplateType.CUSTOM) {
              setCollapseActiveKey(['1']);
            }
          }}
        />
      </Form.Item>

      <StyledCollapse
        activeKey={collapseActiveKey}
        expandIconPosition="left"
        onChange={onCollapseChange}
        lazyload={false}
        bordered={false}
      >
        <Collapse.Item header={collapsedTitle} name="1">
          {algorithmType === EnumAlgorithmProjectType.NN_VERTICAL ? (
            <>
              <Form.Item field={TResourceFieldType.WORKER}>
                <InputGroup
                  columns={getAlgorithmColumns(
                    TResourceFieldType.WORKER,
                    ['replicas', 'cpu', 'mem'],
                    disabled,
                    localDisabledList,
                  )}
                  disableAddAndDelete={true}
                />
              </Form.Item>
              <Form.Item field={TResourceFieldType.MASTER}>
                <InputGroup
                  columns={getAlgorithmColumns(
                    TResourceFieldType.MASTER,
                    ['replicas', 'cpu', 'mem'],
                    disabled,
                    localDisabledList,
                  )}
                  disableAddAndDelete={true}
                />
              </Form.Item>
              <Form.Item field={TResourceFieldType.PS}>
                <InputGroup
                  columns={getAlgorithmColumns(
                    TResourceFieldType.PS,
                    ['replicas', 'cpu', 'mem'],
                    disabled,
                    localDisabledList,
                  )}
                  disableAddAndDelete={true}
                />
              </Form.Item>
            </>
          ) : (
            <Form.Item field={TResourceFieldType.WORKER}>
              <InputGroup
                columns={getAlgorithmColumns(
                  TResourceFieldType.WORKER,
                  isTrustedCenter ? ['replicas', 'cpu', 'mem'] : [undefined, 'cpu', 'mem'],
                  disabled,
                  localDisabledList,
                )}
                disableAddAndDelete={true}
              />
            </Form.Item>
          )}
        </Collapse.Item>
      </StyledCollapse>
    </Form>
  );

  function onCollapseChange(key: string, keys: string[]) {
    setCollapseActiveKey(keys);
  }
};

export default ResourceConfig;
