import React, { FC } from 'react';
import styled from 'styled-components';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  width: 50%;
  height: 95px;
  padding: 10px 16px;
  color: var(--gray7);
`;
const Label = styled.label`
  margin-bottom: 15px;
  font-size: 13px;
  line-height: 22px;
`;
const Value = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  color: var(--textColor);
`;

const ProjectCardProp: FC<{ label: string }> = ({ label, children }) => {
  return (
    <Container>
      <Label>{label}</Label>
      <Value>{children}</Value>
    </Container>
  );
};

export default ProjectCardProp;
