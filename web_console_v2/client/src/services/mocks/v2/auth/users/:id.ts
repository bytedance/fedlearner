import { FedRoles } from 'typings/auth';

const fakeUserInfo = {
  data: {
    data: { id: 1, username: 'Mocked Admin', email: 'fl@mocked.com', role: FedRoles.Admin },
  },
  // to mock server error, just tweak the status code below
  status: 200,
};

export default fakeUserInfo;
