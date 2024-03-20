import React, { FC } from 'react';
import styled from 'styled-components';

const Container = styled.div`
  background-color: white;
  margin-bottom: 20px;
  border-radius: 4px;
`;
const Heading = styled.h3`
  margin-bottom: 0;
  font-weight: 600;
  font-size: 16px;
  line-height: 24px;
  color: var(--gray10);
`;
const Body = styled.div`
  width: var(--form-width, 500px);
  margin-top: 32px;
`;

const SecondaryForm: FC<{ title: string }> = ({ title, children }) => {
  return (
    <Container>
      <Heading>{title}</Heading>
      <Body>{children}</Body>
    </Container>
  );
};

export default SecondaryForm;
