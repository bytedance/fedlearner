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

export type Props = {
  /**
   * margin-top
   * @default 0
   */
  top?: number | string;
  /**
   * margin-left
   * @default 0
   */
  left?: number | string;
  /**
   * @description 每个 item 之间的 gap 距离
   * @description.en-US gap between items
   * @default 0
   */
  gap?: number | string;
  /**
   * @default center
   */
  align?: 'center' | 'start' | 'end';
  /**
   * @default start
   */
  justify?:
    | 'start'
    | 'end'
    | 'center'
    | 'stretch'
    | 'space-between'
    | 'space-around'
    | 'space-evenly';
  onClick?: any;
  className?: string;
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
        marginTop: top ? convertToUnit(top) : undefined,
        marginLeft: left ? convertToUnit(left) : undefined,
        ...((props as any).style || {}),
      }}
    >
      {props.children}
    </Container>
  );
};

export default GridRow;
