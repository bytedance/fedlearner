import React from 'react';
import css from 'styled-jsx/css';
import Coffee from '@zeit-ui/react-icons/coffee';
import { Text, useTheme } from '@zeit-ui/react';

function useStyles(theme) {
  return css`
    .empty {
      padding: 32px;
      text-align: center;
    }
  `;
}

export default function Empty({ icon = Coffee, text = 'There\'s nothing here.' }) {
  const theme = useTheme();
  const styles = useStyles(theme);

  const Icon = icon;

  return (
    <div className="empty">
      <Icon />
      <Text type="secondary">{text}</Text>
      <style jsx>{styles}</style>
    </div>
  );
}
