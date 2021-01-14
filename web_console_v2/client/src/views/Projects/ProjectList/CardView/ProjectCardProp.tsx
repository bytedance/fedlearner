import React, { FC } from 'react';
import styled from 'styled-components';
import { MixinEllipsis } from 'styles/mixins';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  width: 50%;
  max-width: 150px;
  height: 95px;
  padding: 10px 16px;
  color: var(--gray7);
`;
const Label = styled.label`
  ${MixinEllipsis()}

  margin-bottom: 15px;
  font-size: 13px;
  line-height: 22px;
`;
const Value = styled.div`
  ${MixinEllipsis()}

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
