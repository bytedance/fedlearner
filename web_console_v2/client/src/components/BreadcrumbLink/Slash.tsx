/* istanbul ignore file */

import React, { ReactElement } from 'react';
import styled from 'styled-components';

const Slash = styled.div`
  display: inline-block;
  width: 1.75px;
  height: 9px;
  transform: matrix(0.87, 0.5, 0.5, -0.87, 0, 0);
  border-radius: 0.5px;
  margin: 7px 2px 0;
  background-color: rgb(var(--gray-4));
`;

function BreadcrumbSlash(): ReactElement {
  return <Slash />;
}

export default BreadcrumbSlash;
