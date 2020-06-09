import React, { useState, useEffect } from 'react';
import css from 'styled-jsx/css';
import { Avatar, Link, Popover, Tabs, useTheme } from '@zeit-ui/react';

function useStyles(theme) {
  return css`
    .header {
      background: ${theme.palette.background};
      color: ${theme.palette.foreground};
      font-size: 16px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.1);
      transition: all 0.2s ease;
    }

    .headerFixed {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1989;
      background: ${theme.palette.background};
      box-shadow: 0 0 15px 0 rgba(0, 0, 0, 0.1);
      transition: all 0.2s ease;
    }

    .headerContent {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: ${theme.layout.pageWidthWithMargin};
      height: 48px;
      margin: 0 auto;
      padding: 0 ${theme.layout.pageMargin};
    }

    .headerContentBlock {
      flex: 1;
      display: flex;
      align-items: center;
      height: 48px;
    }

    .logo {
      cursor: pointer;
      width: 20px;
      margin-top: auto;
      margin-bottom: auto;
    }

    .headerTitle {
      font-weight: 500;
      display: flex;
      align-items: center;
      padding-left: 10px;
    }

    .nav {
      height: 100%;
      margin-left: ${theme.layout.pageMargin};
    }

    .sidebar {
      display: flex;
      align-items: center !important;
    }

    .themeIcon {
      width: 40px !important;
      height: 40px !important;
      display: flex !important;
      justify-content: center !important;
      align-items: center !important;
      margin-right: 5px;
      padding: 0 !important;
    }

    .popover {
      width: 180px !important;
    }
  `;
}

const popoverContent = () => (
  <>
    <Popover.Item>
      <Link href="/">Dashboard</Link>
    </Popover.Item>
    <Popover.Item>
      <Link href="/admin">Admin</Link>
    </Popover.Item>
    <Popover.Item>
      <Link href="/settings">Settings</Link>
    </Popover.Item>
    <Popover.Item>
      <Link href="/docs">Docs</Link>
    </Popover.Item>
    <Popover.Item line />
    <Popover.Item>
      <Link>Logout</Link>
    </Popover.Item>
  </>
);

export default function Header() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const [scrollTop, setScrollTop] = useState(0);
  const fixed = scrollTop > 24;

  useEffect(() => {
    const scrollHandler = () => {
      setScrollTop(document.documentElement.scrollTop);
    };
    document.addEventListener('scroll', scrollHandler);
    return () => document.removeEventListener('scroll', scrollHandler);
  }, [scrollTop]);

  return (
    <div className={fixed ? 'headerFixed' : 'header'}>
      <div className="headerContent">
        <div className="headerContentBlock">
          <div className="logo">
            <svg width="20" viewBox="0 0 75 65" fill={theme.palette.foreground}>
              <path d="M37.59.25l36.95 64H.64l36.95-64z" />
            </svg>
          </div>
          <div className="headerTitle">Fedlearner</div>
          <nav className="nav">
            <Tabs className="menu">
              <Tabs.Item label="Datasets" value="datasets" />
              <Tabs.Item label="Trainings" value="trainings" />
              <Tabs.Item label="Tasks" value="tasks" />
              <Tabs.Item label="Tickets" value="tickets" />
            </Tabs>
          </nav>
        </div>

        <div className="sidebar">
          <Popover content={popoverContent} placement="bottomEnd">
            <Avatar
              src="https://github.com/bytedance.png"
              alt="ByteDance Avatar"
            />
          </Popover>
        </div>
      </div>
      <style jsx>{styles}</style>
    </div>
  );
}
