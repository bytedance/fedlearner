/* istanbul ignore file */

import React, { CSSProperties, FC } from 'react';
import styled from 'styled-components';
import { convertToUnit } from 'shared/helpers';
import { useToggle } from 'react-use';
import { Down } from 'components/IconPark';
import { MixinCommonTransition } from 'styles/mixins';
import { VariableAccessMode } from 'typings/variable';
import { Tooltip } from '@arco-design/web-react';
import VariablePermission from 'components/VariblePermission';
import i18n from 'i18n';
import { CONSTANTS } from 'shared/constants';

const Container = styled.dl<{ style?: CSSProperties }>`
  --propMargin: 8px;
  position: relative;
  display: grid;
  margin: 12px 0;
  padding: 20px 20px 10px 20px;
  border-radius: 2px;
  background-color: rgb(var(--gray-1));
`;
const Prop = styled.dd`
  position: relative;
  display: flex;
  padding: 0 10px;
  padding-left: 18px;
  margin-bottom: var(--propMargin);
  font-size: 13px;
  line-height: 1.3;
  color: rgb(var(--gray-10));

  & > span {
    word-break: break-all;
    overflow: hidden;
  }

  &::before {
    min-width: var(--labelWidth, 'auto');
    margin-right: 5px;
    content: attr(data-label);
    flex-shrink: 0;
    color: var(--textColorSecondary);
  }
`;
const Content = styled.span`
  white-space: pre-wrap;
`;

const PermissionIndicatorContainer = styled.div`
  display: inline-block;
  position: absolute;
  left: 0;
  top: 1px;
`;

const CollapseButton = styled.div`
  ${MixinCommonTransition('background-color')}
  position: absolute;
  bottom: 0;
  left: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 25px;
  height: 25px;
  transform: translate(-50%, 50%);
  padding: 2px 0 1px;
  border-radius: 50%;
  cursor: pointer;
  background-color: rgb(var(--gray-1));

  &:hover {
    background-color: rgb(var(--gray-3));
  }

  > .anticon {
    ${MixinCommonTransition()}
    margin-top: 1px;
    font-size: 10px;
  }

  &.is-reverse {
    padding: 1px 0 2px;
    > .anticon {
      margin-top: -1px;
      transform: rotate(180deg);
    }
  }
`;

type PropertyItem = {
  /** Display label */
  label: string;
  /** Display value */
  value: React.ReactNode;
  /** Is Hidden */
  hidden?: boolean;
  /** AccessMode */
  accessMode?: VariableAccessMode;
};

type Props = {
  /** DataSource */
  properties: Array<PropertyItem>;
  /** How many cols in one row */
  cols?: number;
  colProportions?: number[];
  /**
   * How many rows can be visible when first render, other rows are folded.
   *
   * NOTE: should not <= 0
   */
  initialVisibleRows?: number;
  /**
   * Label min-width pre item
   */
  labelWidth?: number;
  /**
   * min-width pre item
   */
  minWidth?: number;
  /**
   * line-height pre item
   */
  lineHeight?: number;
  /**
   * Vertical align
   */
  align?: 'stretch' | 'start' | 'center' | 'end';
  /**
   * className
   */
  className?: string;
};

export const variableAccessModeToComponentMap: Record<VariableAccessMode, React.FC> = {
  [VariableAccessMode.PEER_READABLE]: VariablePermission.Readable,
  [VariableAccessMode.PEER_WRITABLE]: VariablePermission.Writable,
  [VariableAccessMode.PRIVATE]: VariablePermission.Private,
  [VariableAccessMode.UNSPECIFIED]: VariablePermission.Private,
};

export const variableAccessModeToDescMap: Record<VariableAccessMode, string> = {
  [VariableAccessMode.PEER_READABLE]: i18n.t('workflow.var_auth_read', { prefix: '对侧' }),
  [VariableAccessMode.PEER_WRITABLE]: i18n.t('workflow.var_auth_write', { prefix: '对侧' }),
  [VariableAccessMode.PRIVATE]: i18n.t('workflow.var_auth_private', { prefix: '对侧' }),
  [VariableAccessMode.UNSPECIFIED]: i18n.t('workflow.var_auth_private', { prefix: '对侧' }),
};

const PropertyList: FC<Props> & {
  ModelCenter: React.FC<NewProps>;
} = ({
  properties,
  cols = 2,
  colProportions,
  labelWidth,
  initialVisibleRows,
  lineHeight = 36,
  minWidth = 100,
  align = 'stretch',
  className,
  ...props
}) => {
  // FIXME: remove next-line after basic_envs been remove
  properties = properties.filter((prop) => prop.label !== 'basic_envs');

  const possibleToCollasped =
    initialVisibleRows && initialVisibleRows > 0 && initialVisibleRows * cols < properties.length;
  const [collapsed, toggleCollapsed] = useToggle(
    possibleToCollasped ? properties.length / cols > initialVisibleRows! : false,
  );

  const propsToDisplay = collapsed ? properties.slice(0, cols * initialVisibleRows!) : properties;
  const containerStyle = {
    gridTemplateColumns: (colProportions || Array(cols).fill(1)).map((p) => `${p}fr`).join(' '),
  };

  return (
    <Container {...props} style={containerStyle} className={className || ''}>
      {propsToDisplay
        .filter((item) => !item.hidden)
        .map((item, index) => {
          const PermissionIndicator = item.accessMode
            ? variableAccessModeToComponentMap[item.accessMode]
            : null;
          const title = item.accessMode ? variableAccessModeToDescMap[item.accessMode] : '';
          return (
            <Prop
              key={item.label + index}
              data-label={item.label}
              style={
                {
                  '--labelWidth': convertToUnit(labelWidth || 'auto'),
                  '--lineHeight': convertToUnit(lineHeight) || '',
                  flexBasis: String(100 / cols) + '%',
                  minWidth: convertToUnit(minWidth),
                  alignItems: align,
                } as CSSProperties
              }
            >
              {PermissionIndicator && (
                <PermissionIndicatorContainer>
                  <Tooltip content={title}>
                    <PermissionIndicator />
                  </Tooltip>
                </PermissionIndicatorContainer>
              )}
              <Content>{item.value || CONSTANTS.EMPTY_PLACEHOLDER}</Content>
            </Prop>
          );
        })}
      {possibleToCollasped && (
        <CollapseButton onClick={toggleCollapsed} className={collapsed ? '' : 'is-reverse'}>
          <Down />
        </CollapseButton>
      )}
    </Container>
  );
};

const NewContainer = styled.dl`
  position: relative;
  display: flex;
  flex-wrap: wrap;
  margin: 15px 0;
  padding: 0 20px;
  border-radius: 2px;
  background-color: rgb(var(--gray-1));
`;
const NewProp = styled(Prop)`
  margin-right: 80px;
  line-height: var(--lineHeight, 36px);
  &::before {
    margin-right: 12px;
  }
`;
const Triangle = styled.div`
  position: absolute;
  width: 12px;
  height: 12px;
  left: 16px;
  top: -4px;
  transform: rotate(45deg);
  background: rgb(var(--gray-1));
`;

type NewProps = {
  properties: {
    label: string;
    value: any;
    hidden?: boolean;
  }[];
};

const NewPropertyList: FC<NewProps> = ({ properties, ...props }) => {
  return (
    <NewContainer {...props}>
      {properties
        .filter((item) => !item.hidden)
        .map((item, index) => {
          return (
            <NewProp key={item.label + index} data-label={item.label}>
              <Content>{item.value || CONSTANTS.EMPTY_PLACEHOLDER}</Content>
            </NewProp>
          );
        })}
      <Triangle />
    </NewContainer>
  );
};
PropertyList.ModelCenter = NewPropertyList;

export default PropertyList;
