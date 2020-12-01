import React from 'react'
import { useTranslation } from 'react-i18next'
import Dashboard from 'views/Dashboard'
import Projects from 'views/Projects'
import Workflows from 'views/Workflows'
import DataResources from 'views/DataResources'
import Settings from 'views/Settings'

const routes: FedRouteConfig[] = [
  {
    path: '/',
    exact: true,
    component: function Home() {
      const { t } = useTranslation()
      return <h1>{t('title') + ' ❤️ ' + t('name')}</h1>
    },
    auth: true,
    children: [],
  },
  {
    path: '/dashboard',
    exact: false,
    component: Dashboard,
    auth: true,
    children: [],
  },
  {
    path: '/settings',
    exact: false,
    component: Settings,
    auth: true,
    children: [],
  },
  {
    path: '/projects',
    exact: true,
    component: Projects,
    auth: true,
    children: [],
  },
  {
    path: '/workflows',
    exact: true,
    component: Workflows,
    auth: true,
    children: [],
  },
  {
    path: '/data-resources',
    exact: true,
    component: DataResources,
    auth: true,
    children: [],
  },
]

export default routes
