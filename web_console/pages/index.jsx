import React, { useMemo, useEffect, useState } from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { Button, Card, Text, Link, useTheme } from '@zeit-ui/react';
import FolderPlusIcon from '@zeit-ui/react-icons/folderPlus';
import { fetcher } from '../libs/http';
import Layout from '../components/Layout';
import ActivityListItem from '../components/ActivityListItem';
import JobCard from '../components/JobCard';

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

    .jobs {
      width: 100%;
    }

    .createJobContainer {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      margin: 8px !important;
      min-height: 135px;
      border: 1px dashed #000;
      border-radius: 8px;
    }

    .createJobContainer span {
      margin-top: 10px;
      font-size: 14px;
      line-height: 24px;
    }

    .activity {
      flex: 1;
    }

    @media screen and (min-width: ${theme.layout.pageWidthWithMargin}) {
      .row {
        flex-direction: row;
        flex-wrap: wrap;
      }

      .jobs {
        width: 540px;
        max-width: 100%;
        margin-right: 80px;
      }
    }
  `;
}

export default function Overview() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const router = useRouter();
  const options = useMemo(() => ({
    searchParams: { offset: 0, limit: 10 },
  }), []);
  const [max, setMax] = useState(10);
  const { data } = useSWR(['jobs', options], fetcher);
  const { data: activityData } = useSWR(['activities', options], fetcher);
  const jobs = data?.data.filter((x) => x.metadata).slice(0, max) ?? [];
  const activities = activityData?.data ?? [];
  const goToJob = () => router.push('/datasource/job');

  useEffect(() => {
    // tips: make content fit in one page for different resolution with `max`
    const count = Math.floor((window.innerHeight - 48 - 60 - 62 - 66) / 173.267);
    if (count < max) {
      setMax(count);
    }
  });

  return (
    <Layout>
      <div className="heading">
        <Text h2>Pending Jobs</Text>
        <Button auto type="secondary" onClick={goToJob}>Create Job</Button>
      </div>
      <div className="row">
        <div className="jobs">
          {jobs.length > 0 && jobs.map((x, i) => (
            <JobCard
              key={x.localdata.id}
              job={x}
              style={i > 0 ? { marginTop: theme.layout.gap } : {}}
            />
          ))}
          {jobs.length > 0 && (
            <Text>
              <Link className="colorLink" href="/job" color>View All Jobs</Link>
            </Text>
          )}
          {jobs.length === 0 && (
            <Card shadow style={{ cursor: 'pointer' }} onClick={goToJob}>
              <div className="createJobContainer">
                <FolderPlusIcon size={28} />
                <span>Create Job</span>
              </div>
            </Card>
          )}
        </div>
        <div className="activity">
          <Text h4>Recent Activity</Text>
          {activities.map((x) => <ActivityListItem key={x.id} activity={x} />)}
          {activities.length === 0 && <Text>No activity yet</Text>}
          {activities.length > 0 && (
            <Text>
              <Link className="colorLink" href="/activity" color>View All Activity</Link>
            </Text>
          )}
        </div>
      </div>

      <style jsx>{styles}</style>
    </Layout>
  );
}
