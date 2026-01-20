import React, { FC, useContext, useState } from 'react';
import { COMPOSE_DRAWER_CHANNELS, ComposeDrawerContext, InspectPayload } from '../..';
import { RefModelSharedProps } from './types';
import { Button, Select, Grid } from '@arco-design/web-react';
import { NoAvailable, OptionLabel } from './elements';
import { composSelfRef, parseSelfRef } from '../helpers';
import VariableLinkAnchor from './VariableLinkAnchor';
import PuBSub from 'pubsub-js';
import { Perspective } from '../../DefaultMode';
import { Variable, VariableComponent } from 'typings/variable';
import { algorithmTypeOptionList } from './shared';

const Row = Grid.Row;
const Col = Grid.Col;

const SelfVariable: FC<RefModelSharedProps> = ({ isCheck, value, onChange }) => {
  const { formData } = useContext(ComposeDrawerContext);
  const [algorithmType, setAlgorithmType] = useState('path');
  const [isShowAlgorithmTypeSelect, setIsShowAlgorithmTypeSelect] = useState(() => {
    // e.g. self.variables.${uuid}
    // If compoment type of variable is VariableComponent.AlgorithmSelect, self.variables.${uuid}.path or self.variables.${uuid}.path
    const list = value?.split('.') ?? [];
    if (list.length >= 4) {
      setAlgorithmType(list[list.length - 1]);
    }
    return list.length >= 4;
  });

  if (!formData) {
    return null;
  }

  const selectedVarUuid = parseSelfRef(value);
  const noVariableAvailable = formData.variables.length === 0;
  return (
    <Row gutter={5}>
      <Col span={isShowAlgorithmTypeSelect ? 10 : 20}>
        {noVariableAvailable ? (
          <NoAvailable>
            本任务暂无有效变量,
            <Button type="text" size="small" onClick={onGoVarTabClick}>
              {'点击前往创建'}
            </Button>
          </NoAvailable>
        ) : (
          <Select
            disabled={isCheck}
            value={selectedVarUuid}
            onChange={onSelectChange}
            placeholder={'请选择需要引用的变量'}
            allowClear
          >
            {formData.variables.map((variable, index: number) => {
              return (
                <Select.Option key={variable._uuid + index} value={variable._uuid} extra={variable}>
                  <OptionLabel data-empty-text="// 未命名变量">{variable.name}</OptionLabel>
                </Select.Option>
              );
            })}
          </Select>
        )}
      </Col>

      {isShowAlgorithmTypeSelect && (
        <Col span={10}>
          <Select
            disabled={isCheck}
            defaultValue={algorithmType}
            onChange={onAlgorithmTypeSelectChange}
          >
            {algorithmTypeOptionList.map((item) => {
              return (
                <Select.Option key={item.value} value={item.value}>
                  <OptionLabel>{item.label}</OptionLabel>
                </Select.Option>
              );
            })}
          </Select>
        </Col>
      )}

      {!noVariableAvailable && (
        <VariableLinkAnchor varUuid={selectedVarUuid} disabled={!selectedVarUuid} />
      )}
    </Row>
  );

  function onSelectChange(val: string, options: any) {
    if (
      (options?.extra as Variable)?.widget_schema?.component === VariableComponent.AlgorithmSelect
    ) {
      setIsShowAlgorithmTypeSelect(true);
      onChange?.(`${composSelfRef(val)}.${algorithmTypeOptionList[0].value}`);
    } else {
      setIsShowAlgorithmTypeSelect(false);
      onChange?.(composSelfRef(val));
    }
  }
  function onAlgorithmTypeSelectChange(val: string) {
    // self.variables.ag.path
    onChange?.(`${composSelfRef(selectedVarUuid)}.${val}`);
  }
  function onGoVarTabClick() {
    PuBSub.publish(COMPOSE_DRAWER_CHANNELS.inspect, {
      perspective: Perspective.Variables,
    } as InspectPayload);
  }
};

export default SelfVariable;
