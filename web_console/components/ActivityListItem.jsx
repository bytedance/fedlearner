import React from 'react';
import css from 'styled-jsx/css';
import { Avatar, Link, Text, useTheme } from '@zeit-ui/react';
import { humanizeDuration } from '../utils/time';

function useStyles(theme) {
  return css`
    .event {
      display: flex;
      align-items: center;
      padding: 10px 0px;
      border-bottom: 1px solid ${theme.palette.accents_2};
      font-size: 14px;
    }
  `;
}

function renderRelease(activity) {
  const { creator, created_at, ctx } = activity;
  const { author, html_url, tag_name } = ctx.github;

  return (
    <>
      <Link href={author.html_url} target="_blank" rel="noopenner noreferer">
        <Avatar
          src={author.avatar_url}
          alt={`${creator} Avatar`}
        />
      </Link>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', margin: '0 0 0 10px' }}>
        <Text b>
          <Link href={author.html_url} target="_blank" rel="noopenner noreferer">{creator}</Link>
        </Text>
        <Text style={{ margin: '0 4px' }}>released version</Text>
        <Text b>
          <Link href={html_url} target="_blank" rel="noopenner noreferer">{tag_name}</Link>
        </Text>
      </div>
      <Text type="secondary">{humanizeDuration(created_at)}</Text>
    </>
  );
}

export default function ActivityListItem({ activity }) {
  const theme = useTheme();
  const styles = useStyles(theme);
  const { type } = activity;

  return (
    <div className="event">
      {type === 'release' && renderRelease(activity)}
      {/* render other type of activity here */}
      <style jsx>{styles}</style>
    </div>
  );
}
