import React from 'react';
import css from 'styled-jsx/css';
import { Text, useTheme } from '@zeit-ui/react';

function useStyles(theme) {
  return css`
    .footer {
      padding: 8px 42px;
      border-top: 1px solid ${theme.palette.accents_2};
      text-align: center;
    }

    @media screen and (min-width: ${theme.layout.pageWidthWithMargin}): {
      .footer {
        text-align: start !important;
      }
    }
  `;
}

export default function Footer() {
  const theme = useTheme();
  const styles = useStyles(theme);
  return (
    <div className="footer">
      <Text type="secondary">Copyright © 2020 ByteDance Inc. All rights reserved.</Text>
      <style jsx>{styles}</style>
    </div>
  );
}
