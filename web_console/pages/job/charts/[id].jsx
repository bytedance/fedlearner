import React from 'react';
import useSWR from 'swr';
import { useRouter } from 'next/router';
import { Text, Card, Grid } from '@zeit-ui/react'

import { fetcher } from '../../../libs/http';
import Layout from '../../../components/Layout';
import css from 'styled-jsx/css';

const { converted2Urls } = require('../../../utils/kibana')

function useStyle () {
  return css`
    iframe {
      border: none;
      width: 100%;
      height: 80vh;
    }
  `
}

export default function charts (props) {
  const router = useRouter()
  const styles = useStyle()
  const { id } = router.query
  const { data: jobData } = useSWR(id ? `job/${id}` : null, fetcher);
  const job = jobData ? jobData.data : null;
  const urls = job
  ? converted2Urls(
    job.localdata.job_type, job.localdata.created_at,
    new Date().toISOString(), job.localdata.name
  )
  : []
  return (
    <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
      <Text h2>{job?.localdata.name || 'Loading...'}</Text>
      <Grid.Container gap={2}>
        {urls.map(url =>
          <Grid sm={24} md={24}>
            <Card>
              <iframe src={url}/>
            </Card>
          </Grid>
        )}
      </Grid.Container>
      <style jsx>{styles}</style>
    </Layout>
  )
}