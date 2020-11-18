import React, { ReactElement } from 'react'
import styled from 'styled-components'
import Header from 'components/Header'
import Footer from 'components/Footer'
import RouteViews from 'views'

const AppLayout = styled.div`
  display: grid;
  min-height: calc(100vh + 60px);
  grid-template-areas:
    'header'
    'main-content'
    'footer';

  grid-template-rows: 80px 1fr 60px;
`

const AppHeader = styled(Header)`
  grid-area: header;
  align-self: start;
`

const AppFooter = styled(Footer)`
  grid-area: footer;
`

const AppMainContent = styled.main`
  grid-area: main-content;
  display: flex;
  align-items: center;
  justify-content: center;
`

function App(): ReactElement {
  return (
    <AppLayout>
      <AppHeader />

      <AppMainContent>
        <RouteViews />
      </AppMainContent>

      <AppFooter />
    </AppLayout>
  )
}

export default App
