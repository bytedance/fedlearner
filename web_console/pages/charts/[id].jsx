import React, { useMemo } from 'react';
import useSWR from 'swr';
import { useRouter } from 'next/router';
import css from 'styled-jsx/css';
import { Text, Card, Grid } from '@zeit-ui/react';
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
  `;
}

export default function Chart(props) {
  const router = useRouter();
  const styles = useStyle();
  const { id } = router.query;
  const { data, isValidating } = useSWR(id ? `job/${id}` : null, fetcher);
  const job = data?.data?.localdata;
  const urls = useMemo(() => {
    if (job) return getJobDashboardUrls(job);
    return [];
  }, [job]);

  return (
    <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
      {isValidating && <Text h2>Loading...</Text>}
      {urls.length > 0
        ? (
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
        : <Text h2>No metrics yet :(</Text>}

      <style jsx>{styles}</style>
    </Layout>
  );
}
