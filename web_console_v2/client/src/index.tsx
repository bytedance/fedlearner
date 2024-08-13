import React from 'react';
import ReactDOM from 'react-dom';
import { ReactQueryDevtools } from 'react-query/devtools';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { BrowserRouter } from 'react-router-dom';
import MockDevtools from 'components/MockDevtools/MockControlPanel';
import App from './App';
import { ThemeProvider } from 'styled-components';
import { RecoilRoot } from 'recoil';
import { setUseWhatChange } from '@simbathesailor/use-what-changed';
import { ConfigProvider } from '@arco-design/web-react';
import { defaultTheme } from 'styles';

import NoResult from 'components/NoResult';

setUseWhatChange(process.env.NODE_ENV === 'development');

ReactDOM.render(
  <BrowserRouter basename="/v2">
    <RecoilRoot>
      <ConfigProvider
        renderEmpty={() => {
          return <NoResult.NoData />;
        }}
      >
        <ThemeProvider theme={defaultTheme}>
          <QueryClientProvider client={queryClient}>
            <App />
            <ReactQueryDevtools position="bottom-right" initialIsOpen={false} />
          </QueryClientProvider>

          <MockDevtools />
        </ThemeProvider>
      </ConfigProvider>
    </RecoilRoot>
  </BrowserRouter>,
  document.getElementById('root'),
);
