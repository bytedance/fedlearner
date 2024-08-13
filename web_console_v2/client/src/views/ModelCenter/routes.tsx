const INDEX_PATH = '/model-center';
const ModelTrain = `${INDEX_PATH}/model-train`;
const ModelEvaluation = `${INDEX_PATH}/:module(model-evaluation|offline-prediction)`;
const OfflinePrediction = ModelEvaluation;

const routes: Record<string, string> = {
  ModelTrain,
  ModelTrainList: `${ModelTrain}/list`,
  ModelTrainCreate: `${ModelTrain}/:role(receiver|sender)/:action(create|edit)/:id?`,
  ModelTrainDetail: `${ModelTrain}/detail/:id`,
  ModelTrainJobCreate: `${ModelTrain}/model-train-job/:type/:id/:step`,
  ModelTrainCreateCentralization: `${ModelTrain}/:role(receiver|sender)/create-centralization/:id?`,

  ModelWarehouse: `${INDEX_PATH}/model-warehouse`,

  ModelEvaluation,
  ModelEvaluationList: `${ModelEvaluation}/list`,
  ModelEvaluationCreate: `${ModelEvaluation}/:role(receiver|sender)/:action(create|edit)/:id?`,
  ModelEvaluationDetail: `${ModelEvaluation}/detail/:id/:tab(result|info)?`,

  OfflinePrediction,
  OfflinePredictionList: `${OfflinePrediction}/list`,
  OfflinePredictionCreate: `${OfflinePrediction}/:role(receiver|sender)/:action(create|edit)/:id?`,
  OfflinePredictionDetail: `${OfflinePrediction}/detail/:id/:tab(result|info)?`,
};

export default routes;

export enum ModelEvaluationModuleType {
  Evaluation = 'model-evaluation',
  Prediction = 'offline-prediction',
}

export enum ModelEvaluationCreateRole {
  Receiver = 'receiver',
  Sender = 'sender',
}

export enum ModelEvaluationCreateAction {
  Create = 'create',
  Edit = 'edit',
}

export enum ModelEvaluationDetailTab {
  Result = 'result',
  Info = 'info',
}

export interface ModelEvaluationListParams {
  module: ModelEvaluationModuleType;
}

export interface ModelEvaluationCreateParams extends ModelEvaluationListParams {
  role: ModelEvaluationCreateRole;
  action: ModelEvaluationCreateAction;
  id: string;
}

export interface ModelEvaluationDetailParams extends ModelEvaluationListParams {
  tab: ModelEvaluationDetailTab;
  id: string;
}
