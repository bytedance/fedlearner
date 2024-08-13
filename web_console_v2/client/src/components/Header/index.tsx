/* istanbul ignore file */

import React, { useState } from 'react';
import styled from 'styled-components';
import { useLocation } from 'react-router-dom';

import { useGetLogoSrc } from 'hooks';

import { isInWorkspace } from 'components/Sidebar';
import ProjectSelectNew from './ProjectSelectNew';
import HeaderAccount from './Account';
import HeaderVersion from './Version';

import { StyledComponetProps } from 'typings/component';

export const Z_INDEX_HEADER = 1001;
export const Z_INDEX_GREATER_THAN_HEADER = 1002;

const Container = styled.header`
  position: sticky;
  z-index: ${Z_INDEX_HEADER}; // > Drawer's 1000
  top: 0;
  display: grid;
  align-items: center;
  grid-template-areas: 'logo project-select . version account-info';
  grid-template-columns: auto auto 1fr auto auto;
  gap: 12px;
  height: var(--headerHeight);
  padding-left: var(--headerPaddingLeft, 30px);
  padding-right: var(--headerPaddingRight, 30px);
  background-color: var(--headerBackground);
  color: white;
  border-bottom: var(--headerBorderBottomWidth) solid var(--headerBorderBottomColor);
`;
const LogoLink = styled.a`
  grid-area: logo;
`;
const Logo = styled.img`
  height: var(--headerLogoHeight);
`;

function Header({ className }: StyledComponetProps) {
  const { primaryLogo } = useGetLogoSrc();

  const location = useLocation();

  const [isHidden] = useState(() => {
    const { pathname } = location;
    return !isInWorkspace(pathname);
  });

  return (
    <Container className={className} id="page-header">
      <LogoLink href="/">
        <Logo src={primaryLogo} alt="Federation Learner logo" />
      </LogoLink>
      <ProjectSelectNew isHidden={isHidden} />
      {/* This empty element is used to fill the blank sapce */}
      <div className="empty" />
      <HeaderVersion />
      <HeaderAccount />
    </Container>
  );
}

export default Header;
