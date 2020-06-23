import React, { useState, useEffect, useCallback } from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { Avatar, Link, Popover, Spinner, Tabs, Loading, useTheme } from '@zeit-ui/react';
import { fetcher } from '../libs/http';
import { logout } from '../services';

function useStyles(theme) {
  return css`
    .space-holder {
      /* headerContent + header border */
      height: 49px;
    }

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

    .popover {
      width: 180px !important;
    }
  `;
}

export default function Header() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const router = useRouter();
  const { data } = useSWR('user', fetcher);
  const { route, query } = router;
  const isAdmin = route.startsWith('/admin/');
  const user = data ? data.data : null;
  const [signingOut, setSigningOut] = useState(false);
  const [scrollTop, setScrollTop] = useState(0);
  const fixed = scrollTop > 24;
  const onSignOut = async (e) => {
    e.preventDefault();
    setSigningOut(true);
    const { error } = await logout();
    setSigningOut(false);
    if (!error) {
      router.push('/login');
    }
  };
  const title = isAdmin ? 'Admin' : 'Fedlearner';
  const navs = isAdmin
    ? [
      { label: 'Federations', value: '/admin/federation' },
      { label: 'Users', value: '/admin/user' },
    ]
    : [
      { label: 'Overview', value: '/' },
      { label: 'Jobs', value: '/jobs' },
      { label: 'Tickets', value: '/ticket' },
    ];

  const PopoverContent = (
    <>
      {user && (
        <Popover.Item title>
          <p>{user.name}</p>
          <p style={{ color: '#666' }}>@{user.username}</p>
        </Popover.Item>
      )}
      <Popover.Item>
        {isAdmin ? <Link href="/">Dashboard</Link> : <Link href="/admin">Admin</Link>}
      </Popover.Item>
      <Popover.Item>
        <Link href="/docs">Docs</Link>
      </Popover.Item>
      <Popover.Item>
        <Link href="/settings">Settings</Link>
      </Popover.Item>
      <Popover.Item line />
      {signingOut
        ? <Loading />
        : (
          <Popover.Item>
            <Link onClick={onSignOut}>Sign out</Link>
          </Popover.Item>
        )}
    </>
  );

  const activeTab = router.pathname;

  const onTabChange = useCallback((value) => router.push(value), [router]);

  useEffect(() => {
    const scrollHandler = () => {
      setScrollTop(document.documentElement.scrollTop);
    };
    document.addEventListener('scroll', scrollHandler);
    return () => document.removeEventListener('scroll', scrollHandler);
  }, [scrollTop]);

  return (
    <div className="space-holder">
      <div className={fixed ? 'headerFixed' : 'header'}>
        <div className="headerContent">
          <div className="headerContentBlock">
            <Link href="/" className="logo">
              <svg width="20" viewBox="0 0 75 65" fill={theme.palette.foreground}>
                <path d="M37.59.25l36.95 64H.64l36.95-64z" />
              </svg>
            </Link>
            <div className="headerTitle">{title}</div>
            <nav className="nav">
              <Tabs className="menu" value={activeTab} onChange={onTabChange}>
                {navs.map((x) => <Tabs.Item key={x.value} label={x.label} value={x.value} />)}
              </Tabs>
            </nav>
          </div>

          <div className="sidebar">
            <Popover content={PopoverContent} placement="bottomEnd">
              {user
                ? (
                  <Avatar
                    src={`https://github.com/${user.username}.png`}
                    alt={`${user.name} Avatar`}
                    style={{ cursor: 'pointer' }}
                  />
                )
                : <Spinner />}
            </Popover>
          </div>
        </div>
      </div>
      <style jsx>{styles}</style>
    </div>
  );
}
