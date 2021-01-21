import React, { FC } from 'react';
import styled from 'styled-components';
import { Col } from 'antd';
import { convertToUnit } from 'shared/helpers';

const Container = styled.dl`
  display: flex;
  flex-wrap: wrap;
  margin: 15px 0;
  padding: 7px 16px;
  background-color: var(--gray1);
`;
const Prop = styled.dd`
  margin-bottom: 0;
  font-size: 13px;
  line-height: 36px;

  &::before {
    display: inline-block;
    min-width: var(--labelWidth, 'auto');
    margin-right: 5px;
    content: attr(data-label) ': ';
    color: var(--textColorSecondary);
  }
`;

type Props = {
  properties: {
    label: string;
    value: any;
  }[];
  cols?: 1 | 2 | 3 | 4 | 6;
  labelWidth?: number;
};

const PropertyList: FC<Props> = ({ properties, cols = 2, labelWidth }) => {
  return (
    <Container>
      {properties.map((item) => {
        return (
          <Col span={24 / cols}>
            <Prop
              data-label={item.label}
              style={{ '--labelWidth': convertToUnit(labelWidth || 'auto') } as any}
            >
              {item.value}
            </Prop>
          </Col>
        );
      })}
    </Container>
  );
};

export default PropertyList;
