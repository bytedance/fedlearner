import React, { FC, useContext, useEffect, useState } from 'react';
import { NoAvailable, OptionLabel } from './elements';
import { Select, Grid, Button } from '@arco-design/web-react';
import {
  definitionsStore,
  JobDefinitionFormWithoutSlots,
  TPL_GLOBAL_NODE_UUID,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { ComposeDrawerContext, COMPOSE_DRAWER_CHANNELS, InspectPayload } from '../..';
import { RefModelSharedProps } from './types';
import { composeOtherJobRef, parseOtherJobRef } from '../helpers';
import VariableLinkAnchor from './VariableLinkAnchor';
import PubSub from 'pubsub-js';
import { Perspective } from '../../DefaultMode';
import { algorithmTypeOptionList } from './shared';
import { Variable, VariableComponent } from 'typings/variable';

const Row = Grid.Row;
const Col = Grid.Col;

type JobList = (JobDefinitionFormWithoutSlots & { uuid: string })[];

const OtherJobVariable: FC<RefModelSharedProps> = ({ isCheck, value, onChange }) => {
  const context = useContext(ComposeDrawerContext);

  // workflow.jobs['186d1db127359'].variables.186d1db127359
  const [jobUuid, varUuid, algorithmType] = parseOtherJobRef(value);

  const [localJobUuid, setLocalJob] = useState(jobUuid);
  const [localVarUuid, setLocalVar] = useState(varUuid);
  const [isShowAlgorithmTypeSelect, setIsShowAlgorithmTypeSelect] = useState(
    Boolean(algorithmType),
  );

  const [jobList, setJobList] = useState<JobList>([]);

  useEffect(() => {
    const tmp: JobList = [];
    definitionsStore.entries.forEach(([uuid, jobDef]) => {
      if (uuid !== TPL_GLOBAL_NODE_UUID && uuid !== context.uuid) {
        tmp.push({ ...jobDef, uuid });
      }
    });

    setJobList(tmp);
  }, [context.uuid]);

  const hasOtherJobs = jobList.length !== 0;
  const availableVariables = jobList.find((item) => localJobUuid === item.uuid)?.variables ?? [];
  const hasVariables = availableVariables.length !== 0;

  if (!hasOtherJobs) {
    return <NoAvailable>暂不存在其他任务</NoAvailable>;
  }

  return (
    <Row gutter={5}>
      <Col span={isShowAlgorithmTypeSelect ? 8 : 10}>
        <Select
          disabled={isCheck}
          value={jobUuid}
          placeholder={'目标任务'}
          onChange={onJobChangeChange}
          allowClear
        >
          {jobList.map((item, index: number) => {
            return (
              <Select.Option key={item.uuid + index} value={item.uuid}>
                <OptionLabel data-empty-text="//未命名任务">{item.name}</OptionLabel>
              </Select.Option>
            );
          })}
        </Select>
      </Col>

      {localJobUuid && (
        <Col span={isShowAlgorithmTypeSelect ? 8 : 12}>
          {!hasVariables ? (
            <NoAvailable>
              该任务暂无变量,
              <Button
                disabled={isCheck}
                type="text"
                size="small"
                onClick={onGoTheJobToCreateVarClick}
              >
                {'点击前往创建'}
              </Button>
            </NoAvailable>
          ) : (
            <Select
              value={varUuid}
              disabled={!localJobUuid || isCheck}
              placeholder={'目标变量'}
              onChange={onVarChangeChange}
              allowClear
            >
              {availableVariables.map((item, index: number) => {
                return (
                  <Select.Option key={item._uuid + index} value={item._uuid} extra={item}>
                    <OptionLabel data-empty-text="// 未命名变量">{item.name}</OptionLabel>
                  </Select.Option>
                );
              })}
            </Select>
          )}
        </Col>
      )}

      {isShowAlgorithmTypeSelect && (
        <Col span={6}>
          <Select
            disabled={isCheck}
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

      {localJobUuid && hasVariables && (
        <VariableLinkAnchor
          jobUuid={jobUuid}
          varUuid={varUuid}
          disabled={!localJobUuid || !localVarUuid || isCheck}
        />
      )}
    </Row>
  );

  function onJobChangeChange(val: string) {
    setLocalJob(val);
    setLocalVar(undefined as any);
    setIsShowAlgorithmTypeSelect(false);

    onChange?.(composeOtherJobRef(val, localVarUuid));
  }
  function onVarChangeChange(val: string, options: any) {
    setLocalVar(val);

    if (
      (options?.extra as Variable)?.widget_schema?.component === VariableComponent.AlgorithmSelect
    ) {
      setIsShowAlgorithmTypeSelect(true);
      onChange?.(`${composeOtherJobRef(localJobUuid, val)}.${algorithmTypeOptionList[0].value}`);
    } else {
      setIsShowAlgorithmTypeSelect(false);
      onChange?.(composeOtherJobRef(localJobUuid, val));
    }
  }
  function onAlgorithmTypeSelectChange(val: string) {
    // workflow.jobs['186d1db127359'].variables.186d1db127359.path
    onChange?.(`${composeOtherJobRef(localJobUuid, localVarUuid)}.${val}`);
  }
  function onGoTheJobToCreateVarClick() {
    if (!localJobUuid) return;
    PubSub.publish(COMPOSE_DRAWER_CHANNELS.inspect, {
      jobUuid: localJobUuid,
      perspective: Perspective.Variables,
    } as InspectPayload);
  }
};

export default OtherJobVariable;
