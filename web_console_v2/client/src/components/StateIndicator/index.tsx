/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import styled from 'styled-components';
import i18n from 'i18n';

import { Tooltip, Tag, Button } from '@arco-design/web-react';
import { IconQuestionCircle } from '@arco-design/web-react/icon';
import { InfoCircle } from 'components/IconPark';
import MoreActions from 'components/MoreActions';

import { TooltipProps } from '@arco-design/web-react/es/Tooltip';
import { TagProps } from '@arco-design/web-react/es/Tag';

const Container = styled.div`
  display: flex;
  align-items: center;
  font-size: var(--textFontSizePrimary);
  line-height: 16px;
  white-space: nowrap;

  &::before {
    content: '●';
    margin-right: 6px;
    font-size: 20px;
    line-height: inherit;
    color: var(--color, var(--custom-color, #e0e0e0));
  }

  &[color='unknown'] {
    --color: var(--backgroundColorGray);
  }
  &[color='success'] {
    --color: rgb(var(--green-6));
  }
  &[color='warning'] {
    --color: rgb(var(--orange-6));
  }
  &[color='error'],
  &[color='deleted'] {
    --color: rgb(var(--red-6));
  }
  &[color='pending_accept'] {
    --color: #fa9600;
  }
  &[color='processing'] {
    --color: rgb(var(--arcoblue-6));
  }
  &[color='gold'] {
    --color: rgb(var(--gold-6));
  }
  &[color='lime'] {
    --color: rgb(var(--lime-6));
  }
`;
const Text = styled.span`
  margin-right: 5px;
`;
const Help = styled.div`
  cursor: help;
`;

const StyledAfterButton = styled(Button)`
  padding: 0 2px;
  height: 20px;
  font-size: 12px;
`;
export interface ActionItem {
  /** Display label */
  label: string;
  onClick?: () => void;
  isLoading?: boolean;
}

export type StateTypes =
  | 'processing'
  | 'success'
  | 'warning'
  | 'error'
  | 'default'
  | 'gold'
  | 'lime'
  | 'unknown'
  | 'pending_accept'
  | 'deleted';

export type ProgressType = 'success' | 'warning' | 'error' | 'normal' | undefined;

type Props = {
  /** State Type, it control color */
  type: StateTypes;
  /** Display text */
  text: string;
  /** Tooptip tip */
  tip?: string;
  /** Enable tag mode */
  tag?: boolean;
  /** Arco component <Tag/> props  */
  tagProps?: TagProps;
  /** <MoreAction/> actionList props */
  actionList?: ActionItem[];
  /** Container style */
  containerStyle?: React.CSSProperties;
  /** Custom render after text layout, if you pass a string, it will render a button */
  afterText?: React.ReactNode;
  /** Only work if afterText is string type */
  onAfterTextClick?: () => void;
  /** Tooptip tip position */
  position?: TooltipProps['position'];
};

type LightClientTypeProps = {
  isLightClient: boolean;
};

const stateTypeToColorMap = {
  default: undefined,
  unknown: 'gray',
  success: 'green',
  warning: 'orange',
  error: 'red',
  deleted: 'red',
  pending_accept: 'orange',
  processing: 'blue',
  gold: 'gold',
  lime: 'lime',
};

const StateIndicator: FC<Props> & {
  LigthClientType: FC<LightClientTypeProps>;
} = ({
  text,
  type = 'default',
  tip,
  position = 'top',
  tag,
  tagProps,
  actionList,
  containerStyle,
  afterText,
  onAfterTextClick,
}) => {
  const Wrapper = tag ? Tag : Container;

  const afterJsx = useMemo(() => {
    if (typeof afterText === 'string') {
      return (
        <StyledAfterButton type="text" size="small" onClick={onAfterTextClick}>
          {afterText}
        </StyledAfterButton>
      );
    }

    return afterText;
  }, [afterText, onAfterTextClick]);

  if (actionList && actionList.length > 0) {
    return (
      <Wrapper color={type} style={containerStyle}>
        <Text>{text}</Text>
        {afterJsx}
        <MoreActions actionList={actionList} trigger="hover">
          <InfoCircle />
        </MoreActions>
      </Wrapper>
    );
  }
  if (tag) {
    return (
      <Tooltip content={tip} position={position}>
        <Tag
          id="workflow-state"
          bordered
          color={stateTypeToColorMap[type || 'defualt']}
          style={containerStyle}
          {...tagProps}
        >
          {text}
        </Tag>
      </Tooltip>
    );
  }

  const Content = (
    <Wrapper color={type} style={containerStyle}>
      <Text>{text}</Text>
      {tip && <IconQuestionCircle />}
      {afterJsx}
    </Wrapper>
  );

  if (tip?.trim()) {
    return (
      <Tooltip content={tip}>
        <Help>{Content}</Help>
      </Tooltip>
    );
  }

  return Content;
};

const LigthClientType: FC<LightClientTypeProps> = ({ isLightClient }) => (
  <StateIndicator
    type={isLightClient ? 'processing' : 'default'}
    text={
      isLightClient
        ? i18n.t('project.label_type_light_client')
        : i18n.t('project.label_type_platform')
    }
    tag
  />
);

StateIndicator.LigthClientType = LigthClientType;

export default StateIndicator;
