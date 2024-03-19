/* istanbul ignore file */

import React, { FC, ReactNode } from 'react';
import styled from 'styled-components';
import { Grid } from '@arco-design/web-react';
import { Label, LabelStrong } from 'styles/elements';
import { Copy } from 'components/IconPark';
import ClickToCopy from 'components/ClickToCopy';

const Row = Grid.Row;
const Col = Grid.Col;

export interface Item {
  key: string;
  value: ReactNode;
  isCanCopy?: boolean;
  onClick?: () => void;
}
export interface Props {
  leftSpan?: number;
  rightSpan?: number;
  list: Item[];
}

const StyledRow = styled(Row)`
  margin-top: 16px;
`;
const StyledCopyIcon = styled(Copy)`
  margin-left: 20px;
  font-size: 14px;
  &:hover {
    color: #1664ff;
  }
`;

const PropList: FC<Props> = ({ list, leftSpan = 4, rightSpan = 20 }) => {
  return (
    <>
      {list.map((item) => {
        return (
          <StyledRow>
            <Col span={leftSpan}>
              <Label>{item.key}</Label>
            </Col>
            <Col span={rightSpan}>
              {item.isCanCopy ? (
                <ClickToCopy text={String(item.value)}>
                  <LabelStrong onClick={item.onClick}>
                    {item.value} <StyledCopyIcon />
                  </LabelStrong>
                </ClickToCopy>
              ) : (
                <LabelStrong onClick={item.onClick}>{item.value}</LabelStrong>
              )}
            </Col>
          </StyledRow>
        );
      })}
    </>
  );
};
export default PropList;
