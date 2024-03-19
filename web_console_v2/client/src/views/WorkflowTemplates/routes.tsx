import { WorkflowTemplateMenuType } from 'typings/workflow';

const INDEX_PATH = '/workflow-center';
const WorkflowTmplate = `${INDEX_PATH}/workflow-templates`;

const routes: Record<string, string> = {
  WorkflowTemplateDetail: `${WorkflowTmplate}/detail/:id/:tab(config|list)/:templateType?`,
};

export default routes;

export enum WorkflowTemplateDetailTab {
  Config = 'config',
  List = 'list',
}

export interface WorkflowTemplateDetailParams {
  tab: WorkflowTemplateDetailTab;
  id: string;
  templateType: WorkflowTemplateMenuType;
}
