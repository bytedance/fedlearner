import React from 'react';
import css from 'styled-jsx/css';
import useSWR from 'swr';
import { Divider, Link, Text, useTheme } from '@zeit-ui/react';
import { fetcher } from '../libs/http';
import Layout from '../components/Layout';
import ActivityListItem from '../components/ActivityListItem';
import { humanizeTime } from '../utils/time';

function useStyles(theme) {
  return css`
    .row {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      justify-content: flex-start;
      position: relative;
      min-width: 1px;
      max-width: 100%;
      margin-bottom: ${theme.layout.pageMargin};
    }

    .activity {
      flex: 1;
    }
  `;
}

export default function Activity() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const { data } = useSWR('activities', fetcher);
  const activities = data?.data ?? [];

  return (
    <Layout>
      <Text h2>Activity</Text>
      <Text>Recent activity about <Link href="https://github.com/bytedance/fedlearner" target="_blank" rel="noopenner noreferer">Fedlearner</Link></Text>

      <Divider />

      <div className="activity">
        {activities.map((x) => (
          <div key={x.id}>
            <Text h3>{humanizeTime(x.created_at, 'MMMM D, YYYY')}</Text>
            <ActivityListItem activity={x} />
          </div>
        ))}
        {activities.length === 0 && <Text>No activity yet</Text>}
      </div>

      <style jsx>{styles}</style>
    </Layout>
  );
}
