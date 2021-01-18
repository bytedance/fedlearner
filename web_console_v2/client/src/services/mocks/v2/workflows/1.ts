import { awaitParticipantConfig } from './example';

const get = {
  data: { data: awaitParticipantConfig },
  status: 200,
};

export const put = {
  data: { data: {} },
  status: 200,
};

export default get;
