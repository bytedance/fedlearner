import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';

const Container = styled.div`
  width: 65px;
  margin-left: 166px;
`;

const TextStyle = styled.div`
  font-size: 13px;
  line-height: 22px;
  color: var(--arcoblue6);
  &::before {
    display: inline;
    font-weight: 800;
    content: '+ ';
  }
`;

interface Props {
  onClick: () => void;
}

function AddField({ onClick }: Props): ReactElement {
  const { t } = useTranslation();
  return (
    <Container onClick={onClick}>
      <TextStyle>{t('project.add_parameters')}</TextStyle>
    </Container>
  );
}

export default AddField;
