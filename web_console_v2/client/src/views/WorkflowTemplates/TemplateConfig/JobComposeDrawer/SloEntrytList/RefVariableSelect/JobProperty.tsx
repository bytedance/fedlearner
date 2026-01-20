import React, { FC, useContext, useEffect, useState } from 'react';
import { OptionLabel } from './elements';
import { Select, Grid } from '@arco-design/web-react';
import {
  definitionsStore,
  JobDefinitionFormWithoutSlots,
  TPL_GLOBAL_NODE_UUID,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import { ComposeDrawerContext } from '../../index';
import { RefModelSharedProps } from './types';
import { composeJobPropRef, parseJobPropRef } from '../helpers';

const Row = Grid.Row;
const Col = Grid.Col;

type JobList = (JobDefinitionFormWithoutSlots & { uuid: string })[];

const jobPropOptions = [
  {
    value: 'name',
    label: 'name - 任务名',
  },
];

const JobProperty: FC<RefModelSharedProps> = ({ isCheck, value, onChange }) => {
  const { uuid: selfJobUuid } = useContext(ComposeDrawerContext);

  const [jobUuid, prop] = parseJobPropRef(value);

  const [localJobUuid, setLocalJob] = useState(jobUuid);
  const [localProp, setLocalProp] = useState(prop);

  const [jobList, setJobList] = useState<JobList>([]);

  useEffect(() => {
    setJobList(
      definitionsStore.entries
        .filter(([uuid]) => uuid !== TPL_GLOBAL_NODE_UUID)
        .map(([uuid, jobDef]) => ({ ...jobDef, uuid })),
    );
  }, [selfJobUuid]);

  return (
    <Row gutter={10}>
      <Col span={12}>
        <Select
          disabled={isCheck}
          value={jobUuid === '__SELF__' ? selfJobUuid : jobUuid}
          placeholder={'目标任务'}
          onChange={onJobChangeChange}
        >
          {jobList.map((item, index: number) => {
            return (
              <Select.Option key={item.uuid + index} value={item.uuid}>
                {item.uuid === selfJobUuid ? (
                  <OptionLabel>本任务</OptionLabel>
                ) : (
                  <OptionLabel data-empty-text="//未命名任务">{item.name}</OptionLabel>
                )}
              </Select.Option>
            );
          })}
        </Select>
      </Col>
      <Col span={12}>
        <Select value={prop} disabled={!localJobUuid} placeholder={'属性'} onChange={onPropChange}>
          {jobPropOptions.map((item, index: number) => {
            return (
              <Select.Option key={item.value + index} value={item.value}>
                {item.label}
              </Select.Option>
            );
          })}
        </Select>
      </Col>
    </Row>
  );

  function onJobChangeChange(val: string) {
    setLocalJob(val);
    onChange &&
      onChange(composeJobPropRef({ isSelf: selfJobUuid === val, job: val, prop: localProp }));
  }
  function onPropChange(val: string) {
    setLocalProp(val);
    onChange &&
      onChange(
        composeJobPropRef({ isSelf: selfJobUuid === localJobUuid, job: localJobUuid, prop: val }),
      );
  }
};

export default JobProperty;
