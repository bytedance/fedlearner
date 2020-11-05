import React, { useMemo, useCallback, useRef } from 'react';
import useSWR from 'swr';
import { useRouter } from 'next/router';
import css from 'styled-jsx/css';
import { Text, Card, Grid, useInput, Input, Button } from '@zeit-ui/react';
import { fetcher } from '../../libs/http';
import Layout from '../../components/Layout';
import getJobDashboardUrls from '../../utils/kibana';

function useStyle() {
  return css`
    iframe {
      border: none;
      width: 100%;
      height: 80vh;
    }
    .custom-metrics {
      display: flex;
      align-items: center;
    }
    .label {
      padding: 0 12px;
    }
  `;
}

export default function Chart(props) {
  const router = useRouter();
  const styles = useStyle();
  const { id } = router.query;
  const { data, isValidating } = useSWR(id ? `job/${id}` : null, fetcher);
  const job = data?.data?.localdata;

  const customerUrls = useRef([])
  const urls = useMemo(() => {
    if (job) return getJobDashboardUrls(job);
    return [];
  }, [job]);

  const { state: customMode, reset: resetCustomMode, bindings: customModeBindings } = useInput('avg')
  const { state: customTitle, reset: resetCustomTitle, bindings: customTitleBindings } = useInput('')
  const onAddMetrics = useCallback(() => {
    if (!job) return
    customerUrls.current.unshift(getJobDashboardUrls(job, {customMode, customTitle}))
    resetCustomMode()
    resetCustomTitle()
  }, [job, customMode, customTitle])

  return (
    <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
      <Card style={{marginBottom: '12px'}}>
        <div className="custom-metrics">
          <div className="label">Mode</div>
          <Input width="200px" {...customModeBindings}/>
          <div className="label">Title</div>
          <Input width="200px" {...customTitleBindings}/>
          <Button style={{marginLeft: '12px'}} onClick={onAddMetrics} auto>Add Metrics</Button>
        </div>
      </Card>
      {isValidating && <Text h2>Loading...</Text>}
      {
        customerUrls.current.length > 0 && (
          <Grid.Container gap={2}>
            {customerUrls.current.map((url) => (
              <Grid sm={24} md={24}>
                <Card>
                  <iframe src={url} />
                </Card>
              </Grid>
            ))}
          </Grid.Container>
        )
      }
      {
        urls.length > 0 && (
          <Grid.Container gap={2}>
            {urls.map((url) => (
              <Grid sm={24} md={24}>
                <Card>
                  <iframe src={url} />
                </Card>
              </Grid>
            ))}
          </Grid.Container>
        )
      }
      {
        customerUrls.current.length === 0
          && urls.length === 0
          && <Text h2>No metrics yet :(</Text>
      }

      <style jsx>{styles}</style>
    </Layout>
  );
}
