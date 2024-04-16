import React, { FC } from 'react';
import { Left } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import styled from 'styled-components';

const Container = styled.div`
  cursor: pointer;
`;

type Props = {
  onClick?: (evt: React.MouseEvent) => void;
};

const BackButton: FC<Props> = ({ onClick, children }) => {
  return (
    <Container onClick={onEleClick}>
      <GridRow gap="7.5" align="center">
        <Left style={{ fontSize: 8 }} />
        {children}
      </GridRow>
    </Container>
  );

  function onEleClick(evt: React.MouseEvent) {
    onClick && onClick(evt);
  }
};

export default BackButton;
