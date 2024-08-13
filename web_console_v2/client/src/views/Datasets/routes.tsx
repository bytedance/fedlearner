const INDEX_PATH = '/datasets';

const routes: Record<string, string> = {
  DatasetCreate: `${INDEX_PATH}/:action(create|edit)/source`,
};

export default routes;

export enum DatasetCreateAction {
  Create = 'create',
  Edit = 'edit',
}
