import React, { ReactElement } from 'react'
import styled from 'styled-components'
import Header from 'components/Header'
import Sidebar from 'components/Sidebar'
import Footer from 'components/Footer'
import RouteViews from 'views'
import { Switch, Route, Redirect } from 'react-router-dom'
import Login from 'views/Login'

const AppLayout = styled.div`
  display: grid;
  min-height: 100vh;
  grid-template-areas:
    'header header'
    'sidebar main-content'
    'sidebar footer';
  grid-template-rows: auto 1fr 30px;
  grid-template-columns: auto 1fr;
`

const AppHeader = styled(Header)`
  grid-area: header;
  align-self: start;
`

const AppSidebar = styled(Sidebar)`
  grid-area: sidebar;
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
    <Switch>
      <Route exact path="/login" component={Login} />

      <AppLayout>
        <AppHeader />

        <AppSidebar />

        <AppMainContent>
          <RouteViews />
        </AppMainContent>

        <AppFooter />
      </AppLayout>

      <Route path="*">You are lost</Route>
    </Switch>
  )
}

export default App
