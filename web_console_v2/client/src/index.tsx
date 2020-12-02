import React from 'react'
import ReactDOM from 'react-dom'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ThemeProvider } from 'styled-components'
import { RecoilRoot } from 'recoil'
import defaultTheme from 'styles/_theme'
import './styles/_variables.css'
import './styles/antd-overrides.less'

import './i18n'

ReactDOM.render(
  <BrowserRouter>
    <RecoilRoot>
      <ThemeProvider theme={defaultTheme}>
        <App />
      </ThemeProvider>
    </RecoilRoot>
  </BrowserRouter>,
  document.getElementById('root'),
)
