import React from 'react';
import css from 'styled-jsx/css';
import { useTheme } from '@zeit-ui/react';
import Header from './Header';
import Footer from './Footer';

function useStyles(theme) {
  return css`
    .layout {
      display: flex;
      flex-direction: column;
      box-sizing: border-box;
      min-height: calc(100vh - 16px);
      background: ${theme.palette.accents_1};
    }

    .content {
      flex: 1;
      width: ${theme.layout.pageWidthWithMargin};
      margin: 0 auto;
      box-sizing: border-box;
    }
  `;
}

export default function Layout({ header = true, footer = true, children }) {
  const theme = useTheme();
  const styles = useStyles(theme);
  return (
    <div className="layout">
      {header && <Header />}
      <div className="content">
        {children}
      </div>
      {footer && <Footer />}

      <style jsx global>{`
        html {
          touch-action: manipulation;
          font-feature-settings: "case" 1,"rlig" 1,"calt" 0;
          text-rendering: optimizeLegibility;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        body {
          margin: 0;
        }

        body, html {
          font-family: "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI","Roboto","Oxygen","Ubuntu","Cantarell","Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
          text-rendering: optimizeLegibility;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          background-color: #fff;
          color: #000;
          scroll-padding-top: 64px;
        }

        svg {
          shape-rendering: crispEdges;
        }

        svg circle,
        svg line,
        svg path,
        svg polygon,
        svg rect {
          shape-rendering: geometricprecision;
        }

        .menu {
          height: 100%;
        }

        .menu header {
          height: inherit;
        }

        .menu .tab {
          padding: 12px !important;
          margin: 0 !important;
        }

        .menu .content {
          display: none;
        }

        .colorLink {
          color: #0070f3 !important;
          text-decoration: none;
          transition: color 0.2s ease 0s;
        }

        .colorLink:hover {
          color: #0070f3 !important;
          text-decoration: underline !important;
        }

        .card .content {
          box-sizing: border-box;
        }

        .card .formCardFooter {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          box-sizing: border-box;
          background: ${theme.palette.accents_1};
        }

        .passwordViwer .input-wrapper {
          border: none !important;
        }

        .passwordViwer .input-wrapper input {
          margin: 0 !important;
          color: #666;
        }

        .formItemWithLabel {
          display: inline-block;
          width: initial;
          box-sizing: border-box;
          -webkit-box-align: center;
        }

        .formItemLabel {
          display: block;
          font-weight: normal;
          color: #444;
          padding: 0 0 0 1px;
          margin-bottom: 8pt;
          font-size: 1rem;
          line-height: 1.5;
        }

        .formItemValue {
          display: -webkit-inline-box;
          display: -webkit-inline-flex;
          display: -ms-inline-flexbox;
          display: inline-flex;
          -webkit-align-items: center;
          -webkit-box-align: center;
          -ms-flex-align: center;
          align-items: center;
          width: initial;
          height: calc(1.687 * 16pt);
        }

        .actionText {
          cursor: pointer;
        }
      `}</style>
      <style jsx>{styles}</style>
    </div>
  );
}
