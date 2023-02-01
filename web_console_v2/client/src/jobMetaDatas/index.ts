/* istanbul ignore file */

import { JobSlot } from 'typings/workflow';
import { JobType } from 'typings/job';

export type JobMetaData = {
  metaYamlString: string;
  slots: { [k: string]: JobSlot };
};

const DataJoin: JobMetaData = {
  metaYamlString: require('./data_join.metayml').default,
  slots: require('./data_join.json'),
};
const PSIDataJoin: JobMetaData = {
  metaYamlString: require('./psi_data_join.metayml').default,
  slots: require('./psi_data_join.json'),
};
const TreeModelEvaluation: JobMetaData = {
  metaYamlString: require('./tree_model_evaluation.metayml').default,
  slots: require('./tree_model_evaluation.json'),
};
const TreeModelTraining: JobMetaData = {
  metaYamlString: require('./tree_model_training.metayml').default,
  slots: require('./tree_model_training.json'),
};
const RawData: JobMetaData = {
  metaYamlString: require('./raw_data.metayml').default,
  slots: require('./raw_data.json'),
};
const NNModelTraining: JobMetaData = {
  metaYamlString: require('./nn_model_training.metayml').default,
  slots: require('./nn_model_training.json'),
};
const NNModelEvaluation: JobMetaData = {
  metaYamlString: require('./nn_model_evaluation.metayml').default,
  slots: require('./nn_model_evaluation.json'),
};
const Transformer: JobMetaData = {
  metaYamlString: require('./transformer.metayml').default,
  slots: require('./transformer.json'),
};

const Analyzer: JobMetaData = {
  metaYamlString: require('./analyzer.metayml').default,
  slots: require('./analyzer.json'),
};

const jobTypeToMetaDatasMap: Map<JobType, JobMetaData> = new Map();

jobTypeToMetaDatasMap.set(JobType.DATA_JOIN, DataJoin);
jobTypeToMetaDatasMap.set(JobType.PSI_DATA_JOIN, PSIDataJoin);
jobTypeToMetaDatasMap.set(JobType.TREE_MODEL_EVALUATION, TreeModelEvaluation);
jobTypeToMetaDatasMap.set(JobType.TREE_MODEL_TRAINING, TreeModelTraining);
jobTypeToMetaDatasMap.set(JobType.RAW_DATA, RawData);
jobTypeToMetaDatasMap.set(JobType.NN_MODEL_EVALUATION, NNModelEvaluation);
jobTypeToMetaDatasMap.set(JobType.NN_MODEL_TRANINING, NNModelTraining);
jobTypeToMetaDatasMap.set(JobType.TRANSFORMER, Transformer);
jobTypeToMetaDatasMap.set(JobType.ANALYZER, Analyzer);

export default jobTypeToMetaDatasMap;
