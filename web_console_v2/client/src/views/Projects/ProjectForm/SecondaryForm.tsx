import React, { FC } from 'react';
import styled from 'styled-components';

const Container = styled.div`
  background-color: white;
  padding: 24px;
  border-radius: 4px;

  &:not(:first-of-type) {
    margin-top: 14px;
  }
`;

const Header = styled.div`
  font-weight: 600;
  font-size: 16px;
  line-height: 24px;
  color: var(--gray10);
`;

const Body = styled.div`
  width: 500px;
  margin-top: 32px;
`;

const SecondaryForm: FC<{ title: string }> = ({ title, children }) => {
  return (
    <Container>
      <Header>{title}</Header>
      <Body>{children}</Body>
    </Container>
  );
};

export default SecondaryForm;
