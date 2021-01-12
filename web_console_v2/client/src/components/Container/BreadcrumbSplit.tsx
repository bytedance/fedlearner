import React, { ReactElement } from 'react';
import styled from 'styled-components';

const SplitContainer = styled.div`
  background-color: #c9cdd4;
  width: 1.75px;
  height: 9px;
  transform: matrix(0.87, 0.5, 0.5, -0.87, 0, 0);
  border-radius: 0.5px;
  margin: 7px 2px 0;
  display: inline-block;
`;

function BreadcrumbSplit(): ReactElement {
  return <SplitContainer />;
}

export default BreadcrumbSplit;
