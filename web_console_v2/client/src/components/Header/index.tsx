import React, { ChangeEvent, useState } from 'react'
import styled from 'styled-components'
import { setLocale } from 'i18n'
import HeaderAccount from './Account'
import { FedLanguages } from 'typings/enum'
import logo from 'assets/images/logo-colorful.svg'
import store from 'store2'
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys'

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
    <Container className={className} id="page-header">
      <LogoLink href="/">
        <img src={logo} alt="Federation Learner logo" />
      </LogoLink>
      <div className="empty" />

      <LanguageSelector name="language-selector" value={lng} onChange={onLanguageChange}>
        <option value="cn">简体中文</option>
        <option value="en">English</option>
      </LanguageSelector>

      <React.Suspense fallback={<div>Loading...</div>}>
        <HeaderAccount />
      </React.Suspense>
    </Container>
  )

  function onLanguageChange(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value as FedLanguages
    setLanguage(value)
    setLocale(value)
    store.set(LOCAL_STORAGE_KEYS, value)
  }
}

export default Header
