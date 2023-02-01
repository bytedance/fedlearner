/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';
import { Button } from '@arco-design/web-react';
import { ButtonProps } from '@arco-design/web-react/lib/Button';

const ButtonContainer = styled(Button)`
  &:hover {
    color: var(--primaryColor);
  }
`;

const IconButton: FC<ButtonProps & { circle?: boolean }> = ({ circle, size, ...props }) => {
  return (
    <ButtonContainer
      type="default"
      shape={circle ? 'circle' : undefined}
      {...props}
      size={size || 'small'}
    />
  );
};

export default IconButton;
