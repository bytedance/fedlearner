import React, { ChangeEvent, useState } from 'react'
import styled from 'styled-components'
import { setLocale } from 'i18n'
import HeaderAccount from './Account'
import { FedLanguages } from 'typings/enum'
import logo from 'assets/images/logo-colorful.svg'

const Container = styled.header`
  position: sticky;
  top: 0;
  display: grid;
  align-items: center;
  grid-template-areas: 'logo . language account-info';
  grid-template-columns: auto 1fr auto auto;
  gap: 20px;
  height: 60px;
  padding: 0 30px;
  background-color: var(--headerBg);
  color: white;
  /* box-shadow: 0px 1px 2px rgba(26, 34, 51, 0.1); */
  border-bottom: 1px solid var(--gray3);
`

const LogoLink = styled.a`
  grid-area: logo;

  > img {
    height: 30px;
  }
`

const LanguageSelector = styled.select`
  color: var(--textColor);
`

function Header({ className }: StyledComponetProps) {
  const [lng, setLanguage] = useState<string>(FedLanguages.Chinese)

  return (
    <Container className={className}>
      <LogoLink href="/">
        <img src={logo} alt="Federation Learner logo" />
      </LogoLink>
      <div className="empty" />

      <LanguageSelector name="language-selector" value={lng} onChange={onLanguageChange}>
        <option value="cn">简体中文</option>
        <option value="en">English</option>
      </LanguageSelector>

      <HeaderAccount />
    </Container>
  )

  function onLanguageChange(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value as FedLanguages
    setLanguage(value)
    setLocale(value)
  }
}

export default Header
