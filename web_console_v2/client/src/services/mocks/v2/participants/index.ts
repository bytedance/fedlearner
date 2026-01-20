import { participantList } from 'services/mocks/v2/participants/examples';

const get = {
  data: {
    data: participantList,
    page_meta: {},
  },
  status: 200,
};
export default get;
