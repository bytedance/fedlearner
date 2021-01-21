import React, { FC } from 'react';
import styled from 'styled-components';
import { Button } from 'antd';
import { ButtonProps } from 'antd/lib/button/button';

const ButtonContainer = styled(Button)`
  &:hover {
    color: var(--primaryColor);
  }
`;

const IconButton: FC<ButtonProps & { circle?: boolean }> = ({ circle, size, ...props }) => {
  return (
    <ButtonContainer
      type="text"
      shape={circle ? 'circle' : 'round'}
      {...props}
      size={size || 'small'}
    />
  );
};

export default IconButton;
