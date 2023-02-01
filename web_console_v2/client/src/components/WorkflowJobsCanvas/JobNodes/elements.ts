/* istanbul ignore file */

import { convertToUnit } from 'shared/helpers';
import styled from 'styled-components';
import { NODE_WIDTH, NODE_HEIGHT, GLOBAL_CONFIG_NODE_SIZE } from '../helpers';
import { Down } from 'components/IconPark';
import { Tag, Menu } from '@arco-design/web-react';
import { MixinEllipsis } from 'styles/mixins';

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
  &.red {
    --fed-color: var(--red6);
  }
  &.purple {
    --fed-color: var(--purple6);
  }

  &[data-disabled='true'] {
    filter: grayscale(0.8);
    opacity: 0.4;

    > h5 {
      text-decoration: line-through;
    }
  }

  .error-message {
    color: var(--errorColor);
  }
`;

export const JobName = styled.h5`
  ${MixinEllipsis()}
  max-width: calc(100% - 28px);
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
  flex-shrink: 0;
`;

export const JobStatusText = styled.small`
  ${MixinEllipsis}

  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
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
  bottom: 0px;
  right: 10px;
  display: flex;
  align-items: center;
  padding-bottom: 5px;
  line-height: 1.8;
  font-size: 12px;
  color: var(--warningColor);

  &[data-inherited='false'] {
    color: var(--primaryColor);
  }
`;

export const InheritedTag = styled(Tag)`
  transform: scale(0.8);
  cursor: help;
`;

export const ArrowDown = styled(Down)`
  margin-left: 5px;
`;

export const InheritMentItem = styled(Menu.Item)`
  font-size: 11px;
`;
