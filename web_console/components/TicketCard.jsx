import React from 'react';
import css from 'styled-jsx/css';
import { Button, Text, Card, Progress, Dot, Tag, useTheme } from '@zeit-ui/react';

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

export default function TicketCard({ name, type, state, stages, progress, style }) {
  const theme = useTheme();
  const styles = useStyles(theme);
  return (
    <Card shadow className="ticketCard" style={style}>
      <div className="title">
        <Text h3>
          {name}
          <Tag type="secondary" style={{ marginLeft: 10, fontWeight: 500 }}>{type}</Tag>
        </Text>
        <Button size="small" auto>Detail</Button>
      </div>
      <div className="content">
        {stages.map((x) => (
          <div key={x.message} className="stage">
            <Dot type={x.state}>
              <Text type="secondary">{x.message}</Text>
            </Dot>
            <span className="created">{x.overhead}</span>
          </div>
        ))}
      </div>
      <Card.Footer>
        <Progress type={state} value={progress} />
      </Card.Footer>

      <style jsx global>{`
        .ticketCard .content {
          box-sizing: border-box;
        }
      `}</style>
      <style jsx>{styles}</style>
    </Card>
  );
}
