/* istanbul ignore file */

import React, { FC, useState, useEffect } from 'react';
import styled from 'styled-components';

import { Input } from '@arco-design/web-react';

const Container = styled.div<{
  isBlock?: boolean;
}>`
  display: ${(props) => (props.isBlock ? 'block' : 'inline-block')};
`;

const Label = styled.div`
  font-size: 12px;
  color: var(--textColor);
  margin-bottom: 6px;
`;
const Content = styled.div<{
  valueColor?: string;
  onClick?: any;
}>`
  display: inline-block;
  padding: 4px 8px;
  background-color: #f6f7fb;
  font-size: 12px;
  color: ${(props) => props.valueColor || 'var(--textColorStrong)'};
  ${(props) => props.onClick && 'cursor: pointer'};
`;

const HoverInput = styled(Input.TextArea)`
  width: 100%;
  padding: 4px;
  font-weight: 500;
  font-size: 12px;
  background-color: #f6f7fb;
  &:hover {
    background-color: #fff;
    border: 1px solid var(--lineColor);
  }
  &:focus {
    background-color: #fff;
    border-color: var(--primaryColor);
  }
`;

type Props = {
  /** Display title(header) */
  title?: string;
  /** Display content(footer) */
  value?: any;
  /** Value's color */
  valueColor?: string;
  /** Is container display: block, otherwise inline-block */
  isBlock?: boolean;
  /** Is input mode  */
  isInputMode?: boolean;
  /** Is value's type React.ReactElement */
  isComponentValue?: boolean;
  onClick?: () => void;
  onInputBlur?: (str: string) => void;
};

const InfoItem: FC<Props> = ({
  title,
  value,
  valueColor,
  isBlock = false,
  isInputMode = false,
  isComponentValue = false,
  onClick,
  onInputBlur,
}) => {
  const [innerValue, setInnerValue] = useState();

  useEffect(() => {
    if (!isComponentValue) {
      setInnerValue((prevState) => value);
    }
  }, [value, isComponentValue]);

  return (
    <Container isBlock={isBlock}>
      <Label>{title}</Label>
      {isInputMode && !isComponentValue ? (
        <HoverInput
          autoSize={{
            minRows: 1,
            maxRows: 4,
          }}
          value={innerValue}
          onClick={(e) => e.stopPropagation()}
          onChange={(value: string, e) => setInnerValue(e.target.value)}
          onBlur={(e) => {
            e.stopPropagation();
            onInputBlur && onInputBlur(e.target.value);
          }}
        />
      ) : (
        <Content onClick={onClick} valueColor={valueColor}>
          {value}
        </Content>
      )}
    </Container>
  );
};

export default InfoItem;
