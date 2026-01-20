/* istanbul ignore file */

export const TIME_INTERVAL = {
  /** 1.5 min */
  LIST: 90 * 1000,
  /** 10 min */
  FLAG: 10 * 60 * 1000,
  /** 10 min */
  CONNECTION_CHECK: 10 * 60 * 1000,
  /** 10s */
  EXPORT_STATE_CHECK: 10 * 1000,
};

export const CONSTANTS = {
  TIME_INTERVAL,
  DELETED_DATASET_NAME: 'deleted',
  TEMPLATE_LIGHT_CLIENT_DATA_JOIN: 'sys-preset-light-psi-data-join',
  EMPTY_PLACEHOLDER: '-',
};

export const TABLE_COL_WIDTH = {
  NAME: 200,
  ID: 100,
  COORDINATOR: 200,
  TIME: 150,
  OPERATION: 200,
  THIN: 100,
  NORMAL: 150,
  BIG_WIDTH: 200,
};

export default CONSTANTS;
