import React from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { Button, Card, Text, Link, useTheme } from '@zeit-ui/react';
import FolderPlusIcon from '@zeit-ui/react-icons/folderPlus';
import { fetcher } from '../libs/http';
import Layout from '../components/Layout';
import EventListItem from '../components/EventListItem';
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
  const { data } = useSWR('jobs', fetcher);
  const jobs = data ? data.data : [];
  const goToJob = () => router.push('/job');
  return (
    <Layout>
      <div className="heading">
        <Text h2>Pending Jobs</Text>
        <Button auto type="secondary" onClick={goToJob}>Create Job</Button>
      </div>
      <div className="row">
        <div className="jobs">
          {jobs.length > 0 && jobs.map((x) => <JobCard key={x.localdata.id} job={x} />)}
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
          <EventListItem username="marswong" created="10m ago">
            Mars Wong created <Text small>training</Text> ticket with <Text b>JD</Text>
          </EventListItem>
          <EventListItem username="fclh1991" created="1d ago">
            fclh created <Text small>data_join_psi</Text> ticket with <Text b>JD</Text>
          </EventListItem>
          <Text>
            <Link className="colorLink" href="#" color>View All Activity</Link>
          </Text>
        </div>
      </div>
      <style jsx>{styles}</style>
    </Layout>
  );
}
