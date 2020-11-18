import React, { ChangeEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import styled from 'styled-components'
import { setLocale } from 'i18n'
import HeaderAccount from './Account'
import { useTranslation } from 'react-i18next'
import { FedLanguages } from 'typings/enum'
import logo from 'assets/images/logo.svg'

const Container = styled.header`
  position: sticky;
  top: 0;
  display: grid;
  align-items: center;
  grid-template-areas: 'logo menu language account-info';
  grid-template-columns: 200px 1fr;
  grid-auto-columns: auto;
  gap: 20px;
  padding: 0 40px;
  background-color: white;
  border-bottom: 1px solid var(--grayColor);
`

const LogoLink = styled.a`
  grid-area: logo;

  > img {
    width: 100%;
  }
`

const MenuContainer = styled.div`
  grid-area: menu;
  padding-left: 100px;

  > .menu-list {
    display: flex;
    gap: 30px;
  }

  .menu-item > a {
    color: ${(props) => props.theme.blackColor};
  }
`

function Header() {
  const [lng, setLanguage] = useState<string>(FedLanguages.Chinese)
  const { t } = useTranslation()

  return (
    <Container>
      <LogoLink href="/">
        <img src={logo} alt="Federation Learner" />
      </LogoLink>

      <MenuContainer>
        <ul className="menu-list">
          <li className="menu-item">
            <Link to="/dashboard">{t('menu_dashboard')}</Link>
          </li>
          <li className="menu-item">
            <Link to="/settings">{t('menu_settings')}</Link>
          </li>
        </ul>
      </MenuContainer>

      <select name="language-selector" value={lng} onChange={onLanguageChange}>
        <option value="cn">简体中文</option>
        <option value="ja">日本語</option>
        <option value="en">English</option>
      </select>

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
