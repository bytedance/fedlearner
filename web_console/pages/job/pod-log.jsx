import React, { useState, useEffect } from 'react';
import css from 'styled-jsx/css';
import { Loading, Note, Text } from '@zeit-ui/react';

import { fetcher } from '../../libs/http';

function useStyles() {
  return css`
    .status-wrap {
      display: flex;
      justify-content: center;
      margin: 100px 0;
    }
    .log-wrap {
      box-sizing: border-box;
      padding: 10px 20px;
      overflow-y: scroll;
      background: #000;
      color: #FFF;
      height: 100vh;
      font-feature-settings: "liga" 0;
      position: relative;
      font-size: 16px;
      font-family: Consolas, "Courier New", monospace;
      white-space: pre-wrap;
    }
  `;
}

const errorMsg = 'Oops, please close this window and open again.';

function PodLog({ query }) {
  const styles = useStyles();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!query.name || !query.time) {
      setLoading(false);
      setError(errorMsg);
      return;
    }
    fetcher(`job/pod/${query.name}/logs/${query.time}`)
      .then((res) => {
        if (!res.data) {
          setLoading(false);
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

  return (
    <div className="page-pod-log">
      {
        !loading && !error && data
          ? (
            <div className="log-wrap">
              {
                data.map((log) => (
                  <Text p>{log}</Text>
                ))
              }
            </div>
          )
          : (
            <div className="status-wrap">
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
          )
      }
      <style jsx>{styles}</style>
      <style jsx global>{`
        html body {
          margin: 0;
          padding: 0;
          height: 100vh;
        }
      `}</style>
    </div>
  );
}

PodLog.getInitialProps = async function (context) {
  return { query: context.query };
};

export default PodLog;
