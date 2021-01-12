import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { MixinEllipsis } from 'styles/mixins';

interface CardDescribeProps {
  describe: string;
  children: React.ReactNode;
}

const Container = styled.div`
  padding: 10px 16px;
  flex: 1;
`;

const Description = styled.span`
  ${MixinEllipsis()}

  font-size: 13px;
  line-height: 22px;
  color: var(--gray7);
`;

function CardDescribe({ describe, children }: CardDescribeProps): ReactElement {
  return (
    <Container>
      <Description>{describe}</Description>
      {children}
    </Container>
  );
}

export default CardDescribe;
