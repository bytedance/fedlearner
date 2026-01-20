import { ProjectBaseAbilitiesType, ProjectTaskType } from 'typings/project';

type routePathName =
  | 'projects'
  | 'datasets'
  | 'modelCenter'
  | 'workflowCenter'
  | 'trustedCenter'
  | 'algorithmManagement'
  | 'modelServing';
// 当用户没有选择工作区只保留工作区管理和工作流中心
export const ABILITIES_SIDEBAR_MENU_MAPPER: Record<
  routePathName,
  (ProjectBaseAbilitiesType | ProjectTaskType)[]
> = {
  projects: [
    ProjectBaseAbilitiesType.BASE,
    ProjectTaskType.ALIGN,
    ProjectTaskType.HORIZONTAL,
    ProjectTaskType.TRUSTED,
    ProjectTaskType.VERTICAL,
  ],
  datasets: [
    ProjectTaskType.ALIGN,
    ProjectTaskType.HORIZONTAL,
    ProjectTaskType.TRUSTED,
    ProjectTaskType.VERTICAL,
  ],
  modelCenter: [ProjectTaskType.HORIZONTAL, ProjectTaskType.VERTICAL],
  workflowCenter: [
    ProjectBaseAbilitiesType.BASE,
    ProjectTaskType.ALIGN,
    ProjectTaskType.HORIZONTAL,
    ProjectTaskType.TRUSTED,
    ProjectTaskType.VERTICAL,
  ],
  trustedCenter: [ProjectTaskType.TRUSTED],
  algorithmManagement: [
    ProjectTaskType.HORIZONTAL,
    ProjectTaskType.TRUSTED,
    ProjectTaskType.VERTICAL,
  ],
  modelServing: [ProjectTaskType.HORIZONTAL, ProjectTaskType.TRUSTED, ProjectTaskType.VERTICAL],
};
