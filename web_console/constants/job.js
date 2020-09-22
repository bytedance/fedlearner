const JOB_TYPE = {
  data_join: 'data_join',
  psi_data_join: 'psi_data_join',
  tree_model: 'tree_model',
  nn_model: 'nn_model',
}

const JOB_TYPE_CLASS = {
  all: [
    JOB_TYPE.data_join,
    JOB_TYPE.psi_data_join,
    JOB_TYPE.nn_model,
    JOB_TYPE.tree_model
  ],
  datasource: [
    JOB_TYPE.data_join,
    JOB_TYPE.psi_data_join,
  ],
  training: [
    JOB_TYPE.nn_model,
    JOB_TYPE.tree_model
  ],
}


module.exports = {
  JOB_TYPE_CLASS,
  JOB_TYPE,
};
