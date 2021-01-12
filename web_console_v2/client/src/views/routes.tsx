import React from 'react';
import { Redirect } from 'react-router-dom';
import Dashboard from 'views/Dashboard';
import Projects from 'views/Projects';
import Workflows from 'views/Workflows';
import Datasets from 'views/Datasets';
import Settings from 'views/Settings';
import CreateProject from 'views/Projects/CreateProject';
import EditProject from 'views/Projects/EditProject';
import { FedRouteConfig } from 'typings/app';

const routes: FedRouteConfig[] = [
  {
    path: '/',
    exact: true,
    component: () => <Redirect to="/projects" />,
    auth: true,
  },
  {
    path: '/dashboard',
    exact: false,
    component: Dashboard,
    auth: true,
  },
  {
    path: '/settings',
    exact: false,
    component: Settings,
    auth: true,
  },
  {
    path: '/projects',
    component: Projects,
    auth: true,
  },
  {
    path: '/workflows',
    component: Workflows,
    auth: true,
  },
  {
    path: '/datasets',
    component: Datasets,
    auth: true,
  },
  {
    path: '/create-project',
    exact: true,
    component: CreateProject,
    auth: true,
  },
  {
    path: '/projects/edit',
    exact: true,
    component: EditProject,
    auth: true,
  },
];

export default routes;
