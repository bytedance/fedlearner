import React from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import { Button, Text, Card, Dot, Tag, useTheme } from '@zeit-ui/react';

function useStyles(theme) {
  return css`
    .title, .stage {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .created {
      font-size: 14px;
      color: rgb(153, 153, 153) !important;
      margin: 0 0 0 ${theme.layout.gapHalf};
      text-align: right;
    }

    @media screen and (max-width: 540px) {
      .created {
        display: none !important;
      }
    }
  `;
}

export default function JobCard({ job }) {
  const theme = useTheme();
  const styles = useStyles(theme);
  const router = useRouter();
  const { kind, apiVersion, metadata, spec, status, localdata } = job;
  const { id, name, job_type, created_at } = localdata;
  const goToDetail = () => router.push(`/job/${id}`);
  return (
    <Card shadow>
      <div className="title">
        <Text h3>
          {name}
          <Tag type="secondary" style={{ marginLeft: 10, fontWeight: 500 }}>{job_type}</Tag>
        </Text>
        <Button size="small" auto onClick={goToDetail}>Detail</Button>
      </div>
      <div className="content">
        <Dot type={status.appState}>
          <Text type="secondary">{status.appState}</Text>
        </Dot>
      </div>
      <Card.Footer>
        <Text>Created at {created_at}</Text>
      </Card.Footer>

      <style jsx>{styles}</style>
    </Card>
  );
}
