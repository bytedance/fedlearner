import React, { useState, useEffect, useCallback, useMemo } from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { Avatar, Link, Popover, Spinner, Tabs, Loading, useTheme, Select, Spacer } from '@zeit-ui/react';
import { ChevronDown } from '@geist-ui/react-icons'
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

    .menu {
      display: flex;
      color: #444;
    }

    .tab {
      display: flex;
      justify-content: center;
      align-items: center;
      position: relative;
      cursor: pointer;
    }
    .tab.active {
      color: #000;
    }
    .tab.active::after {
      position: absolute;
      content: ' ';
      width: 100%;
      height: 100%;
      border-bottom: 2px solid #000;
    }
    /* tab popover */
    .tab .tabPopoverArea {
      display: none;
      position: absolute;
      top: 100%;
    }
    .tab:hover .tabPopoverArea {
      display: block;
    }
    .tab .tabPopover {
      box-shadow: rgba(0, 0, 0, 0.12) 0px 8px 30px;
      background: #fff;
      border-radius: 5px;
      margin-top: 8px;
      font-size: 16px;
      padding: 8px 0;
    }
    .tabPopover .item {
      padding: 12px 16px;
      text-align: center;
      color: #444;
    }
    .tabPopover .item:hover {
      color: #000;
      background: #eee;
      cursor: pointer;
    }
    /* tab popover end */

    .sidebar {
      display: flex;
      align-items: center !important;
    }

    .popover {
      width: 180px !important;
    }

    .rotate {
      transition: all .3s ease-in-out;
    }
    .tab:hover .rotate {
      transform: rotate(180deg)
    }
  `;
}

function isActive(tabValue, route) {
  if (/^\/datasource/.test(route)) {
    return ['/datasource/job', '/datasource/ticket'].some(el => tabValue === el)
  }
  if (/^\/trainning/.test(route)) {
    return ['/trainning/job', '/trainning/ticket'].some(el => tabValue === el)
  }
  return tabValue === route
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
  const navs = useMemo(() => isAdmin
    ? [
      { label: 'Federations', value: '/admin/federation' },
      { label: 'Users', value: '/admin/user' },
    ]
    : [
      { label: 'Overview', value: '/' },
      // { label: 'Jobs', value: '/job' },
      // { label: 'Tickets', value: '/ticket' },
      { label: 'RawDatas', value: '/raw_data' },
      {
        label: 'DataSource',
        value: '/datasource/job',
        children: [
          { label: 'Job', value: '/datasource/job' },
          { label: 'Tickets', value: '/datasource/tickets' },
        ]
      },
      {
        label: 'Trainning',
        value: '/trainning/job',
        children: [
          { label: 'Job', value: '/trainning/job' },
          { label: 'Tickets', value: '/trainning/tickets' },
        ]
      },
      // { label: 'Trainning', value: '/trainning' },
    ], [isAdmin])

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

  const onTabChange = useCallback((value, e) => {
    e.stopPropagation()
    router.push(value)
  }, [router]);

  useEffect(() => {
    const scrollHandler = () => {
      setScrollTop(document.documentElement.scrollTop);
    };
    document.addEventListener('scroll', scrollHandler);
    return () => document.removeEventListener('scroll', scrollHandler);
  }, [scrollTop]);

  const displayFederationFilter = [
    // '/job',
    '/ticket',
    '/raw_data',
    '/datasource/job',
    '/datasource/tickets',
    '/trainning/job',
    '/trainning/tickets'
  ].some(el => el === route)
  const { data: fedData } = useSWR('federations', fetcher)
  const federations = fedData ? fedData.data : null
  const [currFederation, setCurrFederation] = useState(-1)
  useEffect(() => {
    setCurrFederation(parseInt(localStorage.getItem('federationID')) || -1)
  }, [])
  const onFederationChange = v => {
    localStorage.setItem('federationID', v)
    window.location.reload()
  }

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
              {/* Popover not work with tab */}
              <div className="menu" onChange={onTabChange}>
                {navs.map((x) =>
                  <div
                    className={`tab ${isActive(x.value, router.pathname) ? 'active' : ''}`}
                    key={x.label}
                    onClick={(e) => onTabChange(x.value, e)}
                  >
                    {x.label}
                    {
                      x.children &&
                      <>
                        <Spacer x={.25} inline></Spacer>
                        <div className="rotate">
                          <ChevronDown size={18}/>
                        </div>
                      </>
                    }
                    {
                      x.children && <div className="tabPopoverArea">
                        <div className="tabPopover">
                          {x.children.map(item =>
                            <div
                              key={item.label}
                              className="item"
                              onClick={(e) => onTabChange(item.value, e)}
                            >
                              {item.label}
                            </div>
                          )}
                        </div>
                      </div>
                    }
                  </div>
                )}
              </div>
            </nav>
          </div>

          <div className="sidebar">
            {
              displayFederationFilter &&
              <Select
                value={currFederation && currFederation.toString()}
                onChange={onFederationChange}
                size="small"
                style={{marginRight: '16px'}}
              >
                <Select.Option value="-1">All</Select.Option>
                {federations && federations.map(
                  fed =>
                    <Select.Option key={fed.name} value={fed.id.toString()}>{fed.name}</Select.Option>
                )}
              </Select>
            }
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
