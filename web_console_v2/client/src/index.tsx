import React from 'react';
import ReactDOM from 'react-dom';
import { ReactQueryDevtools } from 'react-query-devtools';
import { BrowserRouter } from 'react-router-dom';
import MockDevtools from 'components/_base/MockDevtools';
import App from './App';
import { ThemeProvider } from 'styled-components';
import { RecoilRoot } from 'recoil';
import defaultTheme from 'styles/_theme';
import 'assets/fonts/ClarityMono/index.less';
import './styles/_variables.css';
import './styles/antd-overrides.less';
import './i18n';

ReactDOM.render(
  <BrowserRouter basename="/v2">
    <RecoilRoot>
      <ThemeProvider theme={defaultTheme}>
        <App />

        <ReactQueryDevtools position="bottom-right" />
        <MockDevtools />
      </ThemeProvider>
    </RecoilRoot>
  </BrowserRouter>,
  document.getElementById('root'),
);
