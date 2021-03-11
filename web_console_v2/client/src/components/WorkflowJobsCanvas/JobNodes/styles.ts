import { convertToUnit } from 'shared/helpers';
import styled from 'styled-components';
import { NODE_WIDTH, NODE_HEIGHT, GLOBAL_CONFIG_NODE_SIZE } from '../helpers';
import { Down } from 'components/IconPark';
import { Tag } from 'antd';

export const Container = styled.div`
  position: relative;
  width: ${convertToUnit(NODE_WIDTH)};
  height: ${convertToUnit(NODE_HEIGHT)};
  background-color: var(--selected-background, white);
  border: 1px solid var(--selected-border-color, transparent);
  padding: 14px 20px;
  border-radius: 4px;

  &.federated-mark {
    box-shadow: 6px 0 0 -2px var(--fed-color, transparent) inset;
  }

  &.blue {
    --fed-color: var(--primaryColor);
  }
  &.green {
    --fed-color: var(--successColor);
  }
  &.yellow {
    --fed-color: var(--darkGold6);
  }
  &.magenta {
    --fed-color: var(--magenta5);
  }
  &.cyan {
    --fed-color: var(--cyan6);
  }
`;

export const JobName = styled.h5`
  font-size: 16px;
  line-height: 20px;
  white-space: nowrap;
  color: var(--textColorStrong);

  &[data-secondary='false'] {
    color: var(--textColorSecondary);
  }
`;

export const StatusIcon = styled.img`
  display: block;
  width: 16px;
  height: 16px;
`;

export const JobStatusText = styled.small`
  font-size: 13px;
  line-height: 1;
  color: var(--textColorSecondary);
`;

export const GlobalConfigNodeContainer = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  height: ${convertToUnit(GLOBAL_CONFIG_NODE_SIZE)};
  border-radius: 50%;
  background-color: var(--selected-background, white);
  border: 1px solid var(--selected-border-color, transparent);
`;

export const InheritButton = styled.div`
  position: absolute;
  bottom: 11px;
  right: 14px;
  display: flex;
  align-items: center;
  padding-bottom: 5px;
  line-height: 1.8;
  font-size: 12px;
  color: var(--primaryColor);

  &[data-inherit='false'] {
    color: var(--warningColor);
  }
`;

export const InheritedTag = styled(Tag)`
  transform: scale(0.8);
`;

export const ArrowDown = styled(Down)`
  margin-left: 5px;
`;
