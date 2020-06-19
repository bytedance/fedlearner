import React from 'react';
import css from 'styled-jsx/css';
import { Button, Text, Link, useTheme } from '@zeit-ui/react';
import Layout from '../components/Layout';
import EventListItem from '../components/EventListItem';
import TicketCard from '../components/TicketCard';

function useStyles(theme) {
  return css`
    .heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: ${theme.layout.pageMargin};
    }

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

    .tasks {
      width: 100%;
    }

    .activity {
      flex: 1;
    }

    @media screen and (min-width: ${theme.layout.pageWidthWithMargin}) {
      .row {
        flex-direction: row;
        flex-wrap: wrap;
      }

      .tasks {
        width: 540px;
        max-width: 100%;
        margin-right: 80px;
      }
    }
  `;
}

export default function Dashboard() {
  const theme = useTheme();
  const styles = useStyles(theme);
  return (
    <Layout>
      <div className="heading">
        <Text h2>Pending Jobs</Text>
        <Button auto type="secondary">Create Job</Button>
      </div>
      <div className="row">
        <div className="tasks">
          <TicketCard
            name="618 Game Ads LTV"
            type="training"
            state="error"
            stages={[
              { state: 'success', message: 'ByteDance validation passed', overhead: '1m' },
              { state: 'success', message: 'JD validation passed', overhead: '1m' },
              { state: 'success', message: '1st data block training', overhead: '10m' },
              { state: 'error', message: '2nd data block training', overhead: '30m' },
            ]}
            progress={61.8}
          />
          <TicketCard
            name="618 Game Payment Join"
            type="data_join_psi"
            state="success"
            stages={[
              { state: 'success', message: 'ByteDance validation passed', overhead: '1m' },
              { state: 'success', message: 'JD validation passed', overhead: '10m' },
              { state: 'success', message: 'All data blocks joined', overhead: '12h' },
            ]}
            progress={100}
            style={{ marginTop: theme.layout.pageMargin }}
          />
          <Text>
            <Link className="colorLink" href="/tasks" color>View All Tasks</Link>
          </Text>
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
            <Link className="colorLink" href="/activity" color>View All Activity</Link>
          </Text>
        </div>
      </div>
      <style jsx>{styles}</style>
    </Layout>
  );
}
