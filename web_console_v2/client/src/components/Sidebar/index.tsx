import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { Link, useLocation } from 'react-router-dom';
import { Dropdown, Menu } from 'antd';
import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import { useToggle } from 'react-use';
import { MixinFlexAlignCenter, MixinSquare } from 'styles/mixins';
import classNames from 'classnames';
import { StyledComponetProps } from 'typings/component';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import {
  Apps,
  DataServer,
  Workbench,
  MenuFold,
  MenuUnfold,
  Settings,
  Interaction,
  UserGroup,
} from 'components/IconPark';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { FedRoles, FedUserInfo } from 'typings/auth';

const Container = styled.aside`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  width: 200px;
  padding: 16px 8px 8px;
  background-color: white;
  box-shadow: 1px 0px 0px var(--lineColor);

  &.isFolded {
    width: 48px;
    padding: 16px 4px 8px;
    align-items: center;

    .ant-menu-item {
      padding-left: 0 !important;
      padding-right: 0;
      text-align: center;

      .anticon {
        margin-right: 0;
      }
    }
  }
`;
const StyledMenu = styled(Menu)`
  flex: 1;
`;
const DropdownLink = styled(Link)`
  &[data-is-active='true'] {
    color: var(--primaryColor);
  }
`;

const FoldButton = styled.div`
  ${MixinSquare(24)}
  ${MixinFlexAlignCenter()}

  display: inline-flex;
  background-color: var(--gray1);
  color: var(--gray6);
  border-radius: 2px;
  cursor: pointer;

  &:hover {
    background-color: var(--gray2);
  }
`;

type MenuRoute = {
  to: string;
  label: string;
  icon: any;
  only?: FedRoles[];
  subRoutes?: Omit<MenuRoute, 'icon'>[];
};

const SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/projects',
    label: 'menu.label_project',
    icon: Apps,
  },
  {
    to: '/workflow-templates',
    label: 'menu.label_workflow_tpl',
    icon: Interaction,
  },
  {
    to: '/workflows',
    label: 'menu.label_workflow',
    icon: Workbench,
  },
  {
    to: '/datasets',
    label: 'menu.label_datasets',
    icon: DataServer,
  },
  {
    to: '/users',
    label: 'menu.label_users',
    icon: UserGroup,
    only: [FedRoles.Admin],
  },
  {
    to: '/settings',
    label: 'menu.label_settings',
    icon: Settings,
    only: [FedRoles.Admin],
  },
];

function Sidebar({ className }: StyledComponetProps) {
  const { t } = useTranslation();
  const [isFolded, toggleFold] = useToggle(store.get(LOCAL_STORAGE_KEYS.sidebar_folded));
  const location = useLocation();
  const userQuery = useRecoilQuery<FedUserInfo>(userInfoQuery);
  const [sidebarMenuItems, setSidebarItems] = useState(SIDEBAR_MENU_ROUTES);

  const activeKeys = _calcActiveKeys(sidebarMenuItems, (location as unknown) as Location);

  useEffect(() => {
    const nextItems = getMenuItemsForThisUser();
    setSidebarItems(nextItems);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userQuery.data]);

  return (
    <Container className={classNames(className, { isFolded })}>
      <StyledMenu mode="inline" selectedKeys={activeKeys} defaultOpenKeys={activeKeys}>
        {sidebarMenuItems.map((menu) => {
          /** Has subroutes */
          if (menu.subRoutes) {
            return renderWithSubRoutes(menu);
          }
          /** Doesn't have subroutes */
          return renderPlainRoute(menu);
        })}
      </StyledMenu>
      <FoldButton onClick={onFoldClick}>{isFolded ? <MenuUnfold /> : <MenuFold />}</FoldButton>
    </Container>
  );

  function onFoldClick() {
    toggleFold();
    store.set(LOCAL_STORAGE_KEYS.sidebar_folded, !isFolded);
  }

  function getMenuItemsForThisUser() {
    return SIDEBAR_MENU_ROUTES.filter((item) => {
      if (!item.only) return true;

      if (!userQuery.data) return false;

      return item.only.includes(userQuery.data.role);
    });
  }

  function renderPlainRoute(menu: MenuRoute) {
    return (
      <Menu.Item key={menu.to}>
        {isFolded ? (
          <Tooltip title={t(menu.label)} placement="right">
            <Link to={menu.to}>
              <menu.icon />
            </Link>
          </Tooltip>
        ) : (
          <>
            <menu.icon />
            <Link to={menu.to}>{t(menu.label)}</Link>
          </>
        )}
      </Menu.Item>
    );
  }

  function renderWithSubRoutes(menu: MenuRoute) {
    if (isFolded) {
      return (
        <Menu.Item key={menu.to}>
          <Dropdown
            placement="bottomRight"
            overlay={
              <Menu>
                {menu.subRoutes?.map((subRoute) => (
                  <Menu.Item key={subRoute.to}>
                    <DropdownLink
                      to={subRoute.to}
                      data-is-active={activeKeys.includes(subRoute.to)}
                    >
                      {t(subRoute.label)}
                    </DropdownLink>
                  </Menu.Item>
                ))}
              </Menu>
            }
          >
            <menu.icon />
          </Dropdown>
        </Menu.Item>
      );
    }

    return (
      <Menu.SubMenu key={menu.to} icon={<menu.icon />} title={t(menu.label)}>
        {menu.subRoutes?.map((subRoute) => (
          <Menu.Item key={subRoute.to}>
            <Link to={subRoute.to}>{t(subRoute.label)}</Link>
          </Menu.Item>
        ))}
      </Menu.SubMenu>
    );
  }
}

function _calcActiveKeys(menuItems: MenuRoute[], location: Location) {
  return menuItems.reduce((ret, item) => {
    if (location.pathname.startsWith(item.to)) {
      ret.push(item.to);
    }
    if (item.subRoutes) {
      item.subRoutes.forEach((subItem) => {
        if (location.pathname.startsWith(subItem.to)) {
          ret.push(subItem.to);
        }
      });
    }
    return ret;
  }, [] as string[]);
}

export default Sidebar;
