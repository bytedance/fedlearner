import React, { FC } from 'react';
import { convertToUnit } from 'shared/helpers';
import styled from 'styled-components';

const Container = styled.div`
  display: grid;
  grid-gap: ${(props: Props) => convertToUnit(props.gap)};
  align-items: ${(props: Props) => props.align || 'center'};
  justify-content: ${(props: Props) => props.justify || 'start'};
  grid-auto-columns: auto;
  grid-template-rows: auto;
  grid-auto-flow: column;
`;

type Props = {
  top?: number | string;
  left?: number | string;
  gap?: number | string;
  align?: 'center' | 'start' | 'end';
  justify?:
    | 'start'
    | 'end'
    | 'center'
    | 'stretch'
    | 'space-between'
    | 'space-around'
    | 'space-evenly';

  onClick?: any;
};

/**
 * Row component with ability to specify gap between items
 */
const GridRow: FC<Props> = ({ top, left, ...props }) => {
  return (
    <Container
      role="grid"
      {...props}
      style={{
        marginTop: convertToUnit(top),
        marginLeft: convertToUnit(left),
        ...((props as any).style || {}),
      }}
    >
      {props.children}
    </Container>
  );
};

export default GridRow;
