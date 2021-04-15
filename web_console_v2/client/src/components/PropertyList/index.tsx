import React, { FC } from 'react';
import styled from 'styled-components';
import { Col } from 'antd';
import { convertToUnit } from 'shared/helpers';
import { useToggle } from 'react-use';
import { Down } from 'components/IconPark';
import { MixinCommonTransition } from 'styles/mixins';

const Container = styled.dl`
  position: relative;
  display: flex;
  flex-wrap: wrap;
  margin: 15px 0;
  padding: 7px 16px;
  border-radius: 2px;
  background-color: var(--gray1);
`;
const Prop = styled.dd`
  display: flex;
  align-items: flex-start;
  margin-bottom: 3px;
  font-size: 13px;
  line-height: var(--lineHeight, 36px);
  word-break: break-all;

  &::before {
    display: inline-block;
    min-width: var(--labelWidth, 'auto');
    margin-right: 5px;
    content: attr(data-label) ': ';
    flex-shrink: 0;
    color: var(--textColorSecondary);
  }
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
  background-color: var(--gray1);

  &:hover {
    background-color: var(--darkGray10);
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

type Props = {
  properties: {
    label: string;
    value: any;
    hidden?: boolean;
  }[];
  cols?: 1 | 2 | 3 | 4 | 6;
  initialVisibleRows?: number; // NOTE: should not <= 0
  labelWidth?: number;
  lineHeight?: number;
};

const PropertyList: FC<Props> = ({
  properties,
  cols = 2,
  labelWidth,
  initialVisibleRows,
  lineHeight = 36,
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

  return (
    <Container {...props}>
      {propsToDisplay
        .filter((item) => !item.hidden)
        .map((item, index) => {
          return (
            <Col span={24 / cols} key={item.label + index}>
              <Prop
                data-label={item.label}
                style={
                  {
                    '--labelWidth': convertToUnit(labelWidth || 'auto'),
                    '--lineHeight': convertToUnit(lineHeight) || '',
                  } as any
                }
              >
                {item.value || '-'}
              </Prop>
            </Col>
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

export default PropertyList;
