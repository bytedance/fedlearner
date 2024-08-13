import React, { FC, useMemo, useState } from 'react';
import { Button, Dropdown, Menu, Tooltip } from '@arco-design/web-react';
import { IconDown } from '@arco-design/web-react/icon';
import { GlobalConfigs } from 'typings/dataset';
import ClickToCopy from 'components/ClickToCopy';
import { TAG_MAPPER } from '../../../shared';
import { Tag } from 'typings/workflow';
import PropertyList from 'components/PropertyList';
import styled from './index.module.less';

type TProps = {
  globalConfigs: GlobalConfigs;
};
// 配置参数信息展示的
const paramsTypes = [Tag.RESOURCE_ALLOCATION, Tag.INPUT_PARAM];
const JobParamsPanel: FC<TProps> = (props: TProps) => {
  const { globalConfigs = {} } = props;
  const [selected, setSelected] = useState('');

  const selectRole = useMemo(() => {
    if (!selected && globalConfigs && Object.keys(globalConfigs).length) {
      return Object.keys(globalConfigs)[0];
    }
    return selected;
  }, [globalConfigs, selected]);

  const panelInfos = useMemo(() => {
    return paramsTypes.map((paramsType) => {
      const paramInfo: any = {
        title: TAG_MAPPER[paramsType],
        properties: [],
      };
      if (!globalConfigs || !selectRole) {
        return [];
      }
      paramInfo.properties = globalConfigs[selectRole].variables
        .filter((variable) => variable.tag === paramsType)
        .map((item) => ({
          label: item.name,
          value: (
            <Tooltip
              position="left"
              content={<ClickToCopy text={item.value}>{item.value}</ClickToCopy>}
            >
              <span>{item.value}</span>
            </Tooltip>
          ),
        }));
      return paramInfo;
    });
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
      <div className={styled.params_panel_header}>
        <h3 className={styled.title}>参数信息</h3>
        <Dropdown droplist={dropList()} position="bl">
          <Button size={'mini'} type="text">
            {selectRole} <IconDown />
          </Button>
        </Dropdown>
      </div>
      <div className={styled.params_panel_container}>
        {panelInfos.map((item, index) => (
          <div className={styled.params_panel_item_wrapper} key={index}>
            <span className={styled.params_panel_label}>{item.title}</span>
            <PropertyList properties={item.properties} cols={2} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default JobParamsPanel;
