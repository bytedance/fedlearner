import React, { FC, useMemo, useState } from 'react';
import { Button, Dropdown, Menu, Tooltip } from '@arco-design/web-react';
import { LabelStrong } from 'styles/elements';
import { IconDown } from '@arco-design/web-react/icon';
import { GlobalConfigs } from 'typings/dataset';
import ClickToCopy from 'components/ClickToCopy';
import { Tag } from 'typings/workflow';
import styled from './index.module.less';

type TProps = {
  globalConfigs: GlobalConfigs;
};

const JobParamsPanel: FC<TProps> = (props: TProps) => {
  const { globalConfigs = {} } = props;
  const [selected, setSelected] = useState('');

  const selectRole = useMemo(() => {
    if (!selected && globalConfigs && Object.keys(globalConfigs).length) {
      return Object.keys(globalConfigs)[0];
    }
    return selected;
  }, [globalConfigs, selected]);

  const resourceAllocations = useMemo(() => {
    if (!globalConfigs || !selectRole) {
      return [];
    }
    return globalConfigs[selectRole].variables.filter(
      (variable) => variable.tag === Tag.RESOURCE_ALLOCATION,
    );
  }, [globalConfigs, selectRole]);

  const inputParams = useMemo(() => {
    if (!globalConfigs || !selectRole) {
      return [];
    }
    return globalConfigs[selectRole].variables.filter(
      (variable) => variable.tag === Tag.INPUT_PARAM,
    );
  }, [globalConfigs, selectRole]);

  const dropList = () => {
    return (
      <Menu onClickMenuItem={(key) => setSelected(key)}>
        {Object.keys(globalConfigs).map((item) => {
          return <Menu.Item key={item}>{item}</Menu.Item>;
        })}
      </Menu>
    );
  };
  return (
    <div>
      <div className={styled.params_header}>
        <LabelStrong fontSize={14} isBlock={true}>
          任务配置
        </LabelStrong>
        <Dropdown droplist={dropList()} position="bl">
          <Button size={'mini'} type="text">
            {selectRole} <IconDown />
          </Button>
        </Dropdown>
      </div>
      <div className={styled.container}>
        <span className={styled.params_label}>资源配置</span>
        <div className={styled.params_body}>
          {resourceAllocations.map((item) => {
            return <ParamListItemRender value={item} justifyContent={'space-between'} />;
          })}
        </div>
        <span className={styled.params_label}>输入参数</span>
        <div className={styled.params_body}>
          {inputParams.map((item) => {
            return <ParamListItemRender value={item} justifyContent={'start'} joiner={true} />;
          })}
        </div>
      </div>
    </div>
  );
};

function ParamListItemRender({
  value = {} as any,
  justifyContent = 'space-between',
  joiner = false,
}) {
  return (
    <li style={{ justifyContent: justifyContent }} key={value.name}>
      <span className={styled.styled_param_span}>
        {
          <Tooltip
            position="left"
            content={<ClickToCopy text={value.name}>{value.name}</ClickToCopy>}
          >
            <span>{value.name}</span>
          </Tooltip>
        }
      </span>
      {joiner ? <span>&nbsp;=&nbsp;</span> : ''}
      <span className={styled.styled_param_span}>
        {
          <Tooltip
            position="left"
            content={<ClickToCopy text={value.value}>{value.value}</ClickToCopy>}
          >
            <span>{value.value}</span>
          </Tooltip>
        }
      </span>
    </li>
  );
}

export default JobParamsPanel;
