import React from 'react';
import styled from 'styled-components';
import HeaderAccount from './Account';
import logo from 'assets/images/logo-colorful.svg';
import { StyledComponetProps } from 'typings/component';

const Container = styled.header`
  position: sticky;
  z-index: 1001; // > Drawer's 1000
  top: 0;
  display: grid;
  align-items: center;
  grid-template-areas: 'logo . language account-info';
  grid-template-columns: auto 1fr auto auto;
  gap: 20px;
  height: 60px;
  padding: 0 30px;
  background-color: var(--headerBackground);
  color: white;
  border-bottom: 1px solid var(--gray3);
`;
const LogoLink = styled.a`
  grid-area: logo;

  > img {
    height: 30px;
  }
`;

// const LanguageSelector = styled.select`
//   color: var(--textColor);
// `

function Header({ className }: StyledComponetProps) {
  // const [lng, setLanguage] = useState<string>(store.get('language'))

  return (
    <Container className={className} id="page-header">
      <LogoLink href="/">
        <img src={logo} alt="Federation Learner logo" />
      </LogoLink>
      {/* This empty element is used to fill the space blank */}
      <div className="empty" />

      {/* <LanguageSelector name="language-selector" value={lng} onChange={onLanguageChange}>
        <option value="cn">简体中文</option>
        <option value="en">English</option>
      </LanguageSelector> */}

      <HeaderAccount />
    </Container>
  );

  // function onLanguageChange(event: ChangeEvent<HTMLSelectElement>) {
  //   const value = event.target.value as FedLanguages
  //   setLanguage(value)
  //   setLocale(value)
  //   store.set(LOCAL_STORAGE_KEYS.language, value)
  // }
}

export default Header;
