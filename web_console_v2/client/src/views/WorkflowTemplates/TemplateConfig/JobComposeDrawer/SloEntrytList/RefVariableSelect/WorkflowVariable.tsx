import React, { FC, useState } from 'react';
import { RefModelSharedProps } from './types';
import { NoAvailable, OptionLabel } from './elements';
import { Button, Select, Grid } from '@arco-design/web-react';
import {
  definitionsStore,
  TPL_GLOBAL_NODE_UUID,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { composeWorkflowRef, parseWorkflowRef } from '../helpers';
import VariableLinkAnchor from './VariableLinkAnchor';
import PubSub from 'pubsub-js';
import { COMPOSE_DRAWER_CHANNELS } from '../..';
import { algorithmTypeOptionList } from './shared';
import { Variable, VariableComponent } from 'typings/variable';

const Row = Grid.Row;
const Col = Grid.Col;

const WorkflowVariable: FC<RefModelSharedProps> = ({ isCheck, value, onChange }) => {
  const [isShowAlgorithmTypeSelect, setIsShowAlgorithmTypeSelect] = useState(() => {
    // e.g. workflow.variables.${uuid}
    // If compoment type of variable is VariableComponent.AlgorithmSelect, workflow.variables.${uuid}.path or workflow.variables.${uuid}.path
    const list = value?.split('.') ?? [];
    return list.length >= 4;
  });

  const globalNodeDef = definitionsStore.getValueById(TPL_GLOBAL_NODE_UUID);
  if (!globalNodeDef || !globalNodeDef?.variables || globalNodeDef?.variables.length === 0) {
    return (
      <NoAvailable>
        暂无全局变量,
        <Button disabled={isCheck} type="text" size="small" onClick={onGoGlobalNodeClick}>
          {'点击前往创建'}
        </Button>
      </NoAvailable>
    );
  }

  const selectVal = parseWorkflowRef(value);

  return (
    <Row gutter={10}>
      <Col span={isShowAlgorithmTypeSelect ? 10 : 20}>
        <Select
          value={selectVal}
          onChange={onSelectChange}
          placeholder={'请选择需要引用的全局变量'}
          allowClear
        >
          {globalNodeDef.variables.map((variable, index: number) => {
            return (
              <Select.Option key={variable.name + index} value={variable._uuid} extra={variable}>
                <OptionLabel data-empty-text="//未命名全局变量">{variable.name}</OptionLabel>
              </Select.Option>
            );
          })}
        </Select>
      </Col>

      {isShowAlgorithmTypeSelect && (
        <Col span={10}>
          <Select
            defaultValue={algorithmTypeOptionList[0].value}
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

      <VariableLinkAnchor
        varUuid={selectVal}
        jobUuid={TPL_GLOBAL_NODE_UUID}
        disabled={!selectVal}
      />
    </Row>
  );

  function onSelectChange(val: string, options: any) {
    if (
      (options?.extra as Variable)?.widget_schema?.component === VariableComponent.AlgorithmSelect
    ) {
      setIsShowAlgorithmTypeSelect(true);
      onChange?.(`${composeWorkflowRef(val)}.${algorithmTypeOptionList[0].value}`);
    } else {
      setIsShowAlgorithmTypeSelect(false);
      onChange?.(composeWorkflowRef(val));
    }
  }
  function onAlgorithmTypeSelectChange(val: string) {
    // self.variables.ag.path
    onChange?.(`${composeWorkflowRef(selectVal)}.${val}`);
  }
  function onGoGlobalNodeClick() {
    PubSub.publish(COMPOSE_DRAWER_CHANNELS.inspect, {
      jobUuid: TPL_GLOBAL_NODE_UUID,
    });
  }
};

export default WorkflowVariable;
