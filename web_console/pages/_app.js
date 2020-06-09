import React from 'react';
import { ZeitProvider, CssBaseline } from '@zeit-ui/react';

export default function FLApp({ Component, pageProps }) {
  return (
    <ZeitProvider>
      <CssBaseline />
      <Component {...pageProps} />
    </ZeitProvider>
  );
}
