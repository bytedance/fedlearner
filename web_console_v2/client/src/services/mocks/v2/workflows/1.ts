import { awaitParticipantConfig, withExecutionDetail } from './examples';

const get = {
  data: { data: withExecutionDetail },
  status: 200,
};

export const put = {
  data: { data: { success: true } },
  status: 200,
};

export default get;
