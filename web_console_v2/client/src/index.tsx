import React from 'react';
import ReactDOM from 'react-dom';
import { ReactQueryDevtools } from 'react-query-devtools';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { BrowserRouter } from 'react-router-dom';
import MockDevtools from 'components/_base/MockDevtools';
import App from './App';
import { ThemeProvider } from 'styled-components';
import { RecoilRoot } from 'recoil';
import defaultTheme from 'styles/_theme';
import antdZhCN from 'antd/lib/locale/zh_CN';
import antdEnUS from 'antd/lib/locale/en_US';
import { ConfigProvider } from 'antd';
import 'assets/fonts/ClarityMono/index.less';
import './styles/_variables.css';
import './styles/antd-overrides.less';
import './i18n';
import i18n from './i18n';

ReactDOM.render(
  <BrowserRouter basename="/v2">
    <RecoilRoot>
      <ConfigProvider locale={i18n.language === 'zh' ? antdZhCN : antdEnUS}>
        <ThemeProvider theme={defaultTheme}>
          <QueryClientProvider client={queryClient}>
            <App />
          </QueryClientProvider>

          <ReactQueryDevtools position="bottom-right" />
          <MockDevtools />
        </ThemeProvider>
      </ConfigProvider>
    </RecoilRoot>
  </BrowserRouter>,
  document.getElementById('root'),
);
