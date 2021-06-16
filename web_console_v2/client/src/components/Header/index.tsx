import React from 'react';
import styled from 'styled-components';
import HeaderAccount from './Account';
import { Tooltip } from 'antd';
import logo from 'assets/images/logo-colorful.svg';
import { StyledComponetProps } from 'typings/component';
import { QuestionCircle } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import ProjectSelect from './ProjectSelect';

export const Z_INDEX_HEADER = 1001;
export const Z_INDEX_GREATER_THAN_HEADER = 1002;

const Container = styled.header`
  position: sticky;
  z-index: ${Z_INDEX_HEADER}; // > Drawer's 1000
  top: 0;
  display: grid;
  align-items: center;
  grid-template-areas: 'logo project-select . help account-info';
  grid-template-columns: auto auto 1fr auto auto;
  gap: 12px;
  height: var(--headerHeight);
  padding: 0 30px;
  background-color: var(--headerBackground);
  color: white;
  border-bottom: 1px solid var(--backgroundColorGray);
`;
const LogoLink = styled.a`
  grid-area: logo;
`;
const Logo = styled.img`
  height: 32px;
`;
const HelpIcon = styled(QuestionCircle)`
  font-size: 14px;
  margin-right: 10px;
  cursor: pointer;
`;

function Header({ className }: StyledComponetProps) {
  const { t } = useTranslation();

  return (
    <Container className={className} id="page-header">
      <LogoLink href="/">
        <Logo src={logo} alt="Federation Learner logo" />
      </LogoLink>

      <ProjectSelect />

      {/* This empty element is used to fill the blank sapce */}
      <div className="empty" />

      <Tooltip title={t('app.help')} placement="bottom">
        <HelpIcon />
      </Tooltip>

      <HeaderAccount />
    </Container>
  );
}

export default Header;
