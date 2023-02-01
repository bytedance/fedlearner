import React from 'react';
import { Redirect } from 'react-router-dom';
import Projects from 'views/Projects';
import Datasets from 'views/Datasets';
import { FedRouteConfig } from 'typings/app';
import { FlagKey } from 'typings/flag';
import { FedRoles } from 'typings/auth';
import NewModelCenter from 'views/ModelCenter';
import ModelServing from 'views/ModelServing';
import Workflows from 'views/Workflows';
import WorkflowTemplates from 'views/WorkflowTemplates';
import AlgorithmAcceptance from 'views/AlgorithmManagement/AlgorithmAcceptance';

import CreateCentralization from './ModelCenter/ModelTrain/CreateCentralization';
import NewModelEvaluationCreate from 'views/ModelCenter/ModelEvaluation/ModelEvaluationCreate';
import NewModelTrainCreate from 'views/ModelCenter/ModelTrain/Create';
import ModelTrainJobCreate from './ModelCenter/ModelTrain/ModelTrainJobCreate';
import NewModelCenterRoutes from 'views/ModelCenter/routes';
import CreatePartner from 'views/Partner/CreatePartner';
import EditPartner from 'views/Partner/EditPartner';
import CreateRawDataset from 'views/Datasets/CreateDataset';
import CreateProcessedDataset from 'views/Datasets/CreateProcessedDataset';
import DatasetCenterRoutes from 'views/Datasets/routes';
import CreateDataSource from './Datasets/CreateDataSource';
import { ABILITIES_SIDEBAR_MENU_MAPPER } from 'shared/router';

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
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.projects,
  },
  {
    path: '/workflow-center/workflows',
    component: Workflows,
    auth: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.workflowCenter,
  },
  {
    path: '/workflow-center/workflow-templates',
    component: WorkflowTemplates,
    auth: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.workflowCenter,
  },
  {
    path: '/datasets',
    component: Datasets,
    auth: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.datasets,
  },
  {
    path: '/settings',
    component: () => import('views/Settings'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/users',
    component: () => import('views/Users'),
    auth: true,
    roles: [FedRoles.Admin],
    async: true,
    flagKeys: [FlagKey.USER_MANAGEMENT_ENABLED],
  },
  {
    path: '/model-center',
    component: NewModelCenter,
    auth: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
  },
  {
    path: '/trusted-center',
    component: () => import('views/TrustedCenter'),
    auth: true,
    async: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.trustedCenter,
  },
  {
    path: '/algorithm-management',
    component: () => import('views/AlgorithmManagement'),
    auth: true,
    async: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.algorithmManagement,
  },
  {
    path: '/model-serving',
    component: ModelServing,
    auth: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelServing,
  },
  {
    path: '/audit',
    component: () => import('views/Audit'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/partners',
    component: () => import('views/Partner'),
    async: true,
    auth: true,
  },
  {
    path: '/operation',
    component: () => import('views/OperationMaintenance'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/dashboard',
    component: () => import('views/Dashboard'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/data_fix',
    component: () => import('views/DataFix'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/composer',
    component: () => import('views/Composer'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/cleanup',
    component: () => import('views/Cleanup'),
    auth: true,
    async: true,
    roles: [FedRoles.Admin],
  },
].filter(Boolean) as FedRouteConfig[];

export const noSidebarRoutes: FedRouteConfig[] = [
  {
    path: '/datasets/raw/create',
    component: CreateRawDataset,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.datasets,
  },
  {
    path: '/datasets/processed/:action(create|edit|authorize)/:id?',
    component: CreateProcessedDataset,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.datasets,
  },
  {
    path: NewModelCenterRoutes.ModelTrainCreateCentralization,
    component: CreateCentralization,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
  },
  {
    path: NewModelCenterRoutes.ModelTrainCreate,
    component: NewModelTrainCreate,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
  },
  {
    path: NewModelCenterRoutes.ModelTrainJobCreate,
    component: ModelTrainJobCreate,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
  },
  {
    path: NewModelCenterRoutes.ModelEvaluationCreate,
    component: NewModelEvaluationCreate,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.modelCenter,
  },
  {
    path: '/partners/create',
    component: CreatePartner,
    auth: true,
    exact: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/partners/edit/:id',
    component: EditPartner,
    auth: true,
    exact: true,
    roles: [FedRoles.Admin],
  },
  {
    path: '/algorithm-management/acceptance/:id',
    component: AlgorithmAcceptance,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.algorithmManagement,
  },
  {
    path: DatasetCenterRoutes.DatasetCreate,
    component: CreateDataSource,
    auth: true,
    exact: true,
    abilitiesSupport: ABILITIES_SIDEBAR_MENU_MAPPER.datasets,
  },
].filter(Boolean) as FedRouteConfig[];

export default routes;
