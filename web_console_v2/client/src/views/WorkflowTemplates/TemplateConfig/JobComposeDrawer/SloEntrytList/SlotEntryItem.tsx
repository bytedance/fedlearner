import React, { ChangeEvent, CSSProperties, FC, useRef, memo, useCallback, useState } from 'react';
import styled from './SlotEntryItem.module.less';
import { SlotEntry } from 'views/WorkflowTemplates/TemplateForm/stores';
import { useToggle } from 'react-use';
import { IconDown, IconQuestionCircle } from '@arco-design/web-react/icon';

import { JobSlotReferenceType } from 'typings/workflow';
import { Summary, Container, Details, Name } from '../elements';
import { Tag, Select, Input, Tooltip, Form } from '@arco-design/web-react';
import { useSubscribe } from 'hooks';

import SelfVariable from './RefVariableSelect/SelfVariable';
import WorkflowVariable from './RefVariableSelect/WorkflowVariable';
import ProjectVariable from './RefVariableSelect/ProjectVariable';
import SystemVariable from './RefVariableSelect/SystemVariable';
import OtherJobVariable from './RefVariableSelect/OtherJobVariable';
import JobProperty from './RefVariableSelect/JobProperty';
import { COMPOSE_DRAWER_CHANNELS, HighlightPayload, scrollDrawerBodyTo } from '..';
import { ValidateErrorEntity } from 'typings/component';
import { isEqual } from 'lodash-es';
import { formatValueToString, parseValueFromString } from 'shared/helpers';

const { DEFAULT, SELF, OTHER_JOB, WORKFLOW, PROJECT, SYSTEM, JOB_PROPERTY } = JobSlotReferenceType;

type RefMeta = { color: string; refWidget: any; label: string };

const SlotRefMetas: Partial<Record<JobSlotReferenceType, RefMeta>> = {
  [DEFAULT]: {
    color: '', // default
    refWidget: null,
    label: '模板默认值',
  },
  [SELF]: {
    color: 'gold',
    refWidget: SelfVariable,
    label: '本任务变量',
  },
  [OTHER_JOB]: {
    color: 'cyan',
    refWidget: OtherJobVariable,
    label: '其他任务变量',
  },
  [JOB_PROPERTY]: {
    color: 'arcoblue',
    refWidget: JobProperty,
    label: '任务属性',
  },
  [WORKFLOW]: {
    color: 'blue',
    refWidget: WorkflowVariable,
    label: '工作流全局变量',
  },
  [PROJECT]: {
    color: 'purple',
    refWidget: ProjectVariable,
    label: '工作区变量',
  },
  [SYSTEM]: {
    color: 'lime',
    refWidget: SystemVariable,
    label: '系统变量',
  },
};

const refOptions = Object.entries(JobSlotReferenceType);

type Props = {
  isCheck?: boolean;
  path: number | string;
  value?: SlotEntry;
  onChange?: (val: SlotEntry) => any;
  style?: CSSProperties;
  className?: string;
};

const SlotEntryItem: FC<Props> = ({ isCheck, path, value, onChange, ...props }) => {
  const [validatePassed, setValidatePassed] = useState<boolean>(true);
  const ref = useRef<HTMLDetailsElement>(null);
  const [isOpen, toggleOpen] = useToggle(_shouldInitiallyOpen(value));
  const [hasError, toggleError] = useToggle(false);
  const [highlighted, setHighlight] = useToggle(false);
  const refValTimer = useRef<number>(null);

  const onRefValChange = useCallback((val: string) => {
    refValTimer.current && clearTimeout(refValTimer.current);

    (refValTimer.current as any) = (setTimeout(() => {
      toggleError(!val);
    }, 200) as unknown) as any;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useSubscribe(
    COMPOSE_DRAWER_CHANNELS.broadcast_error,
    (_: string, errInfo: ValidateErrorEntity) => {
      const hasError = errInfo.errorFields.some((field) => {
        const [pathL1] = field.name;
        const reg = RegExp(/_slotEntries/g);
        return reg.test(pathL1) && pathL1 === path;
      });

      toggleError(hasError);

      if (hasError) {
        toggleOpen(true);
      }
    },
  );
  useSubscribe(COMPOSE_DRAWER_CHANNELS.highlight, (_: string, { slotName }: HighlightPayload) => {
    if (value && slotName === value[0]) {
      setHighlight(true);
      toggleOpen(true);

      // Scroll slot into view
      const verticalMiddleY = (window.innerHeight - 60) / 2;
      const top = ref.current?.offsetTop || verticalMiddleY;
      scrollDrawerBodyTo(top - verticalMiddleY);

      setTimeout(() => {
        setHighlight && setHighlight(false);
      }, 5000);
    }
  });

  if (!value) return null;

  const [slotName, slotConfig] = value;
  const currRefType = slotConfig.reference_type;
  const currRefMeta = SlotRefMetas[currRefType]!;
  const isDefaultRefType = currRefType === DEFAULT;

  return (
    <Details ref={ref as any} data-has-error={hasError} data-open={isOpen} {...props}>
      <Summary
        data-has-error={hasError}
        data-highlighted={highlighted}
        onClick={(evt: any) => onToggle(evt as any)}
      >
        {/*
            Certain HTML elements, like <summary>, <fieldset> and <button>, do not work as flex containers.
            You can work by nesting a div under your summary
            https://stackoverflow.com/questions/46156669/safari-flex-item-unwanted-100-width-css/46163405
        */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: '100%',
          }}
        >
          <Name>
            <Tag color={currRefMeta?.color} style={{ marginRight: 5 }} bordered>
              {currRefMeta?.label}
            </Tag>
            {slotConfig.label || slotName}
            <small className={styled.second_label}> ({slotName}) </small>
            {slotConfig.help && (
              <Tooltip content={slotConfig.help}>
                <IconQuestionCircle disabled={isCheck} style={{ marginLeft: 5 }} />
              </Tooltip>
            )}
          </Name>
          <div style={{ marginLeft: 5 }}>
            <IconDown className={styled.open_indicator} />
          </div>
        </div>
      </Summary>

      <Container style={{ display: isOpen ? 'block' : 'none' }}>
        <Form.Item
          field={getNamePath('reference_type')}
          label={'插槽类型'}
          rules={[{ required: true }]}
        >
          <Select disabled={isCheck} onChange={onTypeChange}>
            {refOptions.map(([key, value]) => (
              <Select.Option key={key} value={value}>
                {`${SlotRefMetas[value]?.label} - ${key}`}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        {!isDefaultRefType && (
          <Form.Item
            field={getNamePath('reference')}
            label={'引用路径'}
            // dependencies={['variables']}
            rules={[
              { required: true },
              {
                match: /^[a-zA-Z_0-9]+(?:(.[a-zA-Z_0-9]+)|(\['[^'"\\]+']))+$/g,
                message: '只允许大小写英文字母数字及下划线的组合',
              },
            ]}
          >
            {currRefMeta.refWidget ? (
              <currRefMeta.refWidget
                isCheck={isCheck}
                key="ref-widget"
                onChange={onRefValChange}
                placeholder={'请补全引用路径'}
              />
            ) : (
              <Input disabled={isCheck} key="ref-default-input" placeholder={'请完善引用路径'} />
            )}
          </Form.Item>
        )}

        <Form.Item
          hidden={!isDefaultRefType}
          field={getNamePath('default_value')}
          label={'默认值'}
          rules={[
            {
              validator: (value: string | undefined, callback: (error?: string) => void) => {
                if (validatePassed) {
                  return;
                }
                callback(`JSON ${slotConfig.value_type} 格式错误`);
              },
            },
          ]}
          formatter={(value: any) => {
            if (validatePassed) {
              return formatValueToString(value, slotConfig.value_type);
            }
            return value;
          }}
          getValueFromEvent={(value) => {
            try {
              const res = parseValueFromString(value, slotConfig.value_type);
              setValidatePassed(true);
              return res;
            } catch (error) {
              setValidatePassed(false);
              return value;
            }
          }}
        >
          <Input disabled={isCheck} placeholder={'默认值'} />
        </Form.Item>
      </Container>
    </Details>
  );

  function getNamePath(name: string) {
    // A slot entry consist with [slotName, slotValue]
    // so the 1 refers to entry's value
    return [path, 1, name].join('.');
  }
  function onTypeChange(val: JobSlotReferenceType) {
    //Reset error status
    toggleError(false);
    // Every time change ref type, reset reference to empty
    onChange && onChange([slotName, { ...slotConfig, reference_type: val, reference: '' }]);
  }
  function onToggle(evt: ChangeEvent<HTMLDetailsElement>) {
    toggleOpen(evt.target.open);
  }
};

function _shouldInitiallyOpen(val: SlotEntry | undefined) {
  if (!val) return false;

  const [, slot] = val;
  return slot.reference_type !== JobSlotReferenceType.DEFAULT && !slot.reference;
}

/**
 * Decide if the item need re-render
 * 1. ignore onChange's ref change
 * 2. use Deep comparison
 */
function _propsAreEqual(
  { onChange: _1, value: oldValue, ...prevProps }: Props,
  { onChange: _2, value: newValue, ...newProps }: Props,
): boolean {
  if (oldValue !== newValue) return false;

  return isEqual(prevProps, newProps);
}

export default memo(SlotEntryItem, _propsAreEqual);
