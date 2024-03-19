/* istanbul ignore file */
import React, { useMemo } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import { Dropdown, Menu, Tooltip } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import classNames from 'classnames';
import { StyledComponetProps } from 'typings/component';
import { useRecoilState, useRecoilValue } from 'recoil';
import { appFlag, appPreference, appState } from 'stores/app';
import {
  Apps,
  Audit,
  Common,
  DataServer,
  File,
  MenuFold,
  MenuUnfold,
  ModelCenter,
  Settings,
  UserGroup,
  Workbench,
  Safe,
  TeamOutlined,
} from 'components/IconPark';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { FedRoles, FedUserInfo } from 'typings/auth';
import { FlagKey } from 'typings/flag';
import { fetchDashboardList } from '../../services/operation';
import { useQuery } from 'react-query';
import './index.less';
import { ProjectBaseAbilitiesType, ProjectTaskType } from 'typings/project';
import { useGetCurrentProjectAbilityConfig } from 'hooks';
import { ABILITIES_SIDEBAR_MENU_MAPPER } from 'shared/router';

type MenuRoute = {
  to: string;
  key?: string;
  label: string;
  icon: any;
  only?: FedRoles[];
  subRoutes?: Omit<MenuRoute, 'icon'>[];
  flagKeys?: string[];
  disabled?: boolean;
  abilitiesSupport?: (ProjectBaseAbilitiesType | ProjectTaskType)[];
};

// the roles with dashboard
const AUTH_DASHBOARD: FedRoles[] = [FedRoles.Admin];
// the path show dashboard
const SHOW_DASHBOARD_PATH = ['operation', 'dashboard', 'data_fix', 'composer', 'cleanup'];

const NORMAL_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/projects',
    label: 'menu.label_project',
    icon: Apps,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
  {
    to: '/datasets',
    label: 'menu.label_datasets',
    icon: DataServer,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.datasets,
    subRoutes: [
      {
        to: '/datasets/data_source',
        label: 'menu.label_datasets_data_source',
      },
      {
        to: '/datasets/raw/my',
        label: 'menu.label_datasets_raw',
      },
      {
        to: '/datasets/processed/my',
        label: 'menu.label_datasets_processed',
      },
      {
        to: '/datasets/task_list',
        label: 'menu.label_datasets_task_list',
      },
    ],
  },
  {
    to: '/model-center',
    label: 'menu.label_model_center',
    icon: ModelCenter,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
    subRoutes: [
      {
        to: '/model-center/model-train/list',
        label: 'menu.label_model_center_model_training',
      },
      {
        to: '/model-center/model-warehouse',
        label: 'menu.label_model_center_model_warehouse',
      },
      {
        to: '/model-center/model-evaluation/list',
        label: 'menu.label_model_center_model_evaluation',
      },
      {
        to: '/model-center/offline-prediction/list',
        label: 'menu.label_model_center_offline_prediction',
      },
    ],
  },
  {
    to: '/workflow-center',
    label: 'menu.label_workflow_center',
    icon: Workbench,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.workflowCenter,
    subRoutes: [
      {
        to: '/workflow-center/workflows',
        label: 'menu.label_workflow',
      },
      {
        to: '/workflow-center/workflow-templates',
        label: 'menu.label_workflow_tpl',
      },
    ],
  },
  {
    to: '/trusted-center',
    label: 'menu.label_trusted_center',
    icon: Safe,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.trustedCenter,
    flagKeys: [FlagKey.TRUSTED_COMPUTING_ENABLED],
  },
  {
    to: '/algorithm-management',
    label: 'menu.label_algorithm_repository',
    icon: File,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.algorithmManagement,
  },
  {
    to: '/model-serving',
    label: 'menu.label_model_serving',
    icon: ModelCenter,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelServing,
    subRoutes: [
      {
        to: '/model-serving',
        label: 'menu.label_model_serving_service',
      },
    ],
  },
].filter(Boolean);
const USER_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/users',
    label: 'menu.label_users',
    icon: UserGroup,
    only: [FedRoles.Admin],
    flagKeys: [FlagKey.USER_MANAGEMENT_ENABLED],
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
];
const SETTING_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/settings',
    label: 'menu.label_settings',
    icon: Settings,
    only: [FedRoles.Admin],
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
    subRoutes: ([
      process.env.REACT_APP_ENABLE_IMAGE_VERSION_PAGE !== 'false' && {
        to: '/settings/image',
        label: 'menu.label_settings_image',
        only: [FedRoles.Admin],
      },
      {
        to: '/settings/variables',
        label: 'menu.label_settings_variables',
        only: [FedRoles.Admin],
      },
    ] as Omit<MenuRoute, 'icon'>[]).filter(Boolean),
  },
];
const AUDIT_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/audit',
    label: 'menu.label_audit_log',
    icon: Audit,
    only: [FedRoles.Admin],
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
    subRoutes: [
      {
        to: '/audit/event',
        label: 'menu.label_event_record',
        only: [FedRoles.Admin],
      },
    ],
  },
];
const OP_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/operation',
    label: 'menu.label_operation_maintenance',
    only: [FedRoles.Admin],
    icon: Common,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
  {
    to: '/data_fix',
    label: 'menu.label_dataset_fix',
    only: [FedRoles.Admin],
    flagKeys: [FlagKey.DATASET_STATE_FIX_ENABLED],
    icon: Settings,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
  {
    to: '/composer',
    label: 'Composer',
    only: [FedRoles.Admin],
    icon: Common,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
    subRoutes: [
      {
        to: '/composer/scheduler-item/list',
        label: '调度程序项',
        only: [FedRoles.Admin],
      },
      {
        to: '/composer/scheduler-runner/list',
        label: '调度程序运行器',
        only: [FedRoles.Admin],
      },
    ],
  },
  {
    to: '/cleanup',
    label: 'Cleanup',
    only: [FedRoles.Admin],
    icon: Common,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
];
const PARTNER_SIDEBAR_MENU_ROUTES: MenuRoute[] = [
  {
    to: '/partners',
    label: 'menu.label_partners',
    icon: TeamOutlined,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
];

/** Not in workspace */
const pathnameToMenuRouteMap: {
  [key: string]: MenuRoute[];
} = {
  users: USER_SIDEBAR_MENU_ROUTES,
  settings: SETTING_SIDEBAR_MENU_ROUTES,
  audit: AUDIT_SIDEBAR_MENU_ROUTES,
  partners: PARTNER_SIDEBAR_MENU_ROUTES,
  operation: OP_SIDEBAR_MENU_ROUTES,
  composer: OP_SIDEBAR_MENU_ROUTES,
  cleanup: OP_SIDEBAR_MENU_ROUTES,
  dashboard: OP_SIDEBAR_MENU_ROUTES,
  data_fix: OP_SIDEBAR_MENU_ROUTES,
};

export function isInWorkspace(pathname: string) {
  const list = pathname.split('/');

  if (list?.[1] && pathnameToMenuRouteMap[list[1]]) {
    return false;
  }
  return true;
}

function Sidebar({ className }: StyledComponetProps) {
  const { t } = useTranslation();
  const history = useHistory();
  const [preference, setPreference] = useRecoilState(appPreference);
  const appStateValue = useRecoilValue(appState);
  const appFlagValue = useRecoilValue(appFlag);
  const location = useLocation();
  const userQuery = useRecoilQuery<FedUserInfo>(userInfoQuery);
  const { abilities } = useGetCurrentProjectAbilityConfig();

  const currentPathName = useMemo(() => {
    const { pathname } = location;
    const list = pathname.split('/');
    return list?.[1] || '';
  }, [location]);

  const dashboardQuery = useQuery('fetchDashboardList', () => fetchDashboardList(), {
    enabled: Boolean(
      userQuery.data?.role &&
        AUTH_DASHBOARD.includes(userQuery.data.role) &&
        SHOW_DASHBOARD_PATH.includes(currentPathName),
    ),
  });

  const dashboards = useMemo(() => {
    if (!dashboardQuery.data) {
      return [];
    }
    return dashboardQuery.data?.data || [];
  }, [dashboardQuery.data]);

  const sidebarMenuItems = useMemo(() => {
    const { pathname } = location;
    return getMenuItemsByAbilities(
      getMenuItemsByFlagKey(getMenuItemsForThisUser(getMenuRoute(pathname))),
      abilities,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userQuery.data, appFlagValue, dashboards, abilities]);

  const activeKeys = _calcActiveKeys(sidebarMenuItems, (location as unknown) as Location);

  return (
    <aside
      className={`side-bar-container ${classNames(className, {
        isFolded: preference.sidebarFolded,
        isHidden: appStateValue.hideSidebar,
      })}`}
    >
      <Menu
        className="side-bar-menu"
        mode="vertical"
        selectedKeys={activeKeys}
        defaultOpenKeys={activeKeys}
        levelIndent={28}
      >
        {sidebarMenuItems.map((menu) => {
          /** Has subroutes */
          if (menu.subRoutes) {
            return renderWithSubRoutes(menu);
          }
          /** Doesn't have subroutes */
          return renderPlainRoute(menu);
        })}
      </Menu>
      <div className="side-bar-fold-button" onClick={onFoldClick}>
        {preference.sidebarFolded ? <MenuUnfold /> : <MenuFold />}
      </div>
    </aside>
  );

  function onFoldClick() {
    setPreference({
      ...preference,
      sidebarFolded: !preference.sidebarFolded,
    });
  }

  function getMenuRoute(pathname: string) {
    const list = pathname.split('/');

    if (list?.[1] && pathnameToMenuRouteMap[list[1]]) {
      // no workspace routes
      let currentMenu = pathnameToMenuRouteMap[list[1]];
      if (
        ['operation', 'dashboard', 'data_fix', 'composer', 'cleanup'].includes(list[1]) &&
        Array.isArray(dashboards)
      ) {
        currentMenu = currentMenu.concat(
          appFlagValue[FlagKey.DASHBOARD_ENABLED]
            ? dashboards.map((item) => ({
                to: `/dashboard/${item.uuid}`,
                label: item.name,
                only: [FedRoles.Admin],
                flagKeys: [FlagKey.DASHBOARD_ENABLED],
                icon: Common,
              }))
            : [
                {
                  to: `/dashboard`,
                  label: '仪表盘',
                  icon: Common,
                },
              ],
        );
      }
      return currentMenu;
    }

    // workspace routes
    return NORMAL_SIDEBAR_MENU_ROUTES;
  }

  function getMenuItemsForThisUser(menuRoutes: MenuRoute[]) {
    return menuRoutes.filter((item) => {
      if (!item.only) return true;

      if (!userQuery.data) return false;

      // Role
      return item.only.includes(userQuery.data.role);
    });
  }

  function renderPlainRoute(menu: MenuRoute) {
    return (
      <Menu.Item
        disabled={menu.disabled}
        key={menu.key || menu.to}
        onClick={() => handleMenuChange(menu.to)}
      >
        {preference.sidebarFolded ? (
          <Tooltip content={t(menu.label)} position="right">
            <menu.icon />
          </Tooltip>
        ) : (
          <>
            <span style={{ display: 'inline-block', marginRight: 14 }}>
              <menu.icon />
            </span>
            {t(menu.label)}
          </>
        )}
      </Menu.Item>
    );
  }

  function renderWithSubRoutes(menu: MenuRoute) {
    if (preference.sidebarFolded) {
      return (
        <Menu.Item disabled={menu.disabled} key={menu.key || menu.to}>
          <Dropdown
            position="br"
            trigger={['click']}
            droplist={
              <Menu>
                {menu.subRoutes?.map((subRoute) => (
                  <Menu.Item
                    disabled={subRoute.disabled}
                    key={subRoute.key || subRoute.to}
                    onClick={() => handleMenuChange(subRoute.to)}
                  >
                    {t(subRoute.label)}
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
      <Menu.SubMenu
        key={menu.key || menu.to}
        title={
          <>
            <span style={{ display: 'inline-block', marginRight: 14 }}>
              <menu.icon />
            </span>
            {t(menu.label)}
          </>
        }
      >
        {menu.subRoutes?.map((subRoute) => (
          <Menu.Item
            disabled={subRoute.disabled}
            key={subRoute.key || subRoute.to}
            onClick={() => handleMenuChange(subRoute.to)}
          >
            {t(subRoute.label)}
          </Menu.Item>
        ))}
      </Menu.SubMenu>
    );
  }

  function getMenuItemsByFlagKey(menuRoutes: MenuRoute[]) {
    return menuRoutes.filter((item) => {
      if (item.subRoutes) {
        item.subRoutes = getMenuItemsByFlagKey((item.subRoutes as MenuRoute[]) || []);
      }

      if (!item.flagKeys) return true;
      if (item.flagKeys.length === 0) return false;

      // Flag key
      // If appFlagValue has one flag(existed in item.flagKeys array), and it's value is false or not exist in appFlagValue
      // so don't show this menu
      return !item.flagKeys.some((flag) => !appFlagValue[flag]);
    });
  }

  function handleMenuChange(target: string) {
    const { pathname } = location;
    if (pathname === target) return null;
    history.push(target);
  }
}

function getMenuItemsByAbilities(
  menuRoutes: MenuRoute[],
  abilities: (ProjectBaseAbilitiesType | ProjectTaskType)[] | undefined,
) {
  if (!abilities?.length) {
    return menuRoutes;
  }
  return menuRoutes.filter((item) => item.abilitiesSupport?.includes(abilities?.[0]));
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
