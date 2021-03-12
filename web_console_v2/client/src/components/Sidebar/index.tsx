import React from 'react';
import styled from 'styled-components';
import { Link, useLocation } from 'react-router-dom';
import { Menu } from 'antd';
import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import { useToggle } from 'react-use';
import { MixinFlexAlignCenter, MixinSquare } from 'styles/mixins';
import classNames from 'classnames';
import { StyledComponetProps } from 'typings/component';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { Apps, DataServer, Workbench, MenuFold, MenuUnfold, Settings } from 'components/IconPark';

const Container = styled.aside`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  width: 200px;
  padding: 16px 8px 8px;
  background-color: white;

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

const SIDEBAR_MENU_ITEMS = [
  {
    to: '/projects',
    label: 'menu.label_project',
    icon: Apps,
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
    to: '/settings',
    label: 'menu.label_settings',
    icon: Settings,
  },
];

function Sidebar({ className }: StyledComponetProps) {
  const { t } = useTranslation();
  const [isFolded, toggleFold] = useToggle(store.get(LOCAL_STORAGE_KEYS.sidebar_folded));
  const location = useLocation();

  const activeMenuItemKey =
    SIDEBAR_MENU_ITEMS.find((item) => location.pathname.startsWith(item.to))?.to || '';

  return (
    <Container className={classNames(className, { isFolded })}>
      <StyledMenu mode="inline" selectedKeys={[activeMenuItemKey]}>
        {SIDEBAR_MENU_ITEMS.map((menu) => (
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
        ))}
      </StyledMenu>

      <FoldButton onClick={onFoldClick}>{isFolded ? <MenuUnfold /> : <MenuFold />}</FoldButton>
    </Container>
  );

  function onFoldClick() {
    toggleFold();
    store.set(LOCAL_STORAGE_KEYS.sidebar_folded, !isFolded);
  }
}

export default Sidebar;
