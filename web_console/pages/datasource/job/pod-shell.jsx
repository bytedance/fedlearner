import React, { useState, useEffect } from 'react';
import css from 'styled-jsx/css';
import { Loading, Note } from '@zeit-ui/react';
import dynamic from 'next/dynamic';

import { fetcher } from '../../../libs/http';

const Shell = dynamic(() => import('../../../components/Shell'), { ssr: false });

function useStyles() {
  return css`
    .page-wrap {
      display: flex;
      justify-content: center;
      margin: 100px 0;
    }
  `;
}

const errorMsg = 'Oops, please close this window and open again.';

function PodShell({ query }) {
  const styles = useStyles();

  const [data, setData] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!query.name) {
      setLoading(false);
      setError(errorMsg);
      return;
    }
    fetcher(`job/pod/${query.name}/container`)
      .then((res) => {
        setLoading(false);
        if (!res.data) {
          setError(res.error || errorMsg);
          return;
        }
        setData(res.data);
      })
      .catch(() => {
        setLoading(false);
        setError(errorMsg);
      });
  }, []);

  if (data) {
    return <Shell {...data} />;
  }

  return (
    <div className="page-pod-shell">
      <div className="page-wrap">
        {
          loading
            ? <Loading />
            : null
        }
        {
          error
            ? <Note type="error">{error}</Note>
            : null
        }
      </div>
      <style jsx>{styles}</style>
    </div>
  );
}

PodShell.getInitialProps = (context) => ({ query: context.query });

export default PodShell;
