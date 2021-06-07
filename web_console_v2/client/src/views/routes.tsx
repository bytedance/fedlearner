import React from 'react';
import { Redirect } from 'react-router-dom';
import Projects from 'views/Projects';
import Workflows from 'views/Workflows';
import WorkflowTemplates from 'views/WorkflowTemplates';
import Datasets from 'views/Datasets';
import Settings from 'views/Settings';
import { FedRouteConfig } from 'typings/app';
import { FedRoles } from 'typings/auth';
import Users from './Users';

const routes: FedRouteConfig[] = [
  {
    path: '/',
    exact: true,
    component: () => <Redirect to="/projects" />,
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
    path: '/workflow-templates',
    component: WorkflowTemplates,
    auth: true,
  },
  {
    path: '/datasets',
    component: Datasets,
    auth: true,
  },
  {
    path: '/settings',
    component: Settings,
    auth: true,
  },
  {
    path: '/users',
    component: Users,
    auth: true,
    roles: [FedRoles.Admin],
  },
];

export default routes;
