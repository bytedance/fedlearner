import React from 'react';
import css from 'styled-jsx/css';
import { Avatar, Text, useTheme } from '@zeit-ui/react';

function useStyles(theme) {
  return css`
    .event {
      display: flex;
      align-items: center;
      padding: 10px 0px;
      border-bottom: 1px solid ${theme.palette.accents_2};
      font-size: 14px;
    }

    .message {
      margin: 0;
      flex: 1;
    }

    .created {
      color: rgb(153, 153, 153) !important;
      margin: 0 0 0 auto;
      padding-left: 10px;
      text-align: right;
    }
  `;
}

export default function EventListItem({ children, username, created }) {
  const theme = useTheme();
  const styles = useStyles(theme);
  return (
    <div className="event">
      <Avatar
        src={`https://vercel.com/api/www/avatar/?u=${username}&s=64`}
        alt={`${username} Avatar`}
      />
      <Text style={{ flex: 1, margin: '0 0 0 10px' }}>{children}</Text>
      <Text type="secondary">{created}</Text>
      <style jsx>{styles}</style>
    </div>
  );
}
