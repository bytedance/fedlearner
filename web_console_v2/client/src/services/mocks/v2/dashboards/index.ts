import { Dashboard } from 'typings/operation';

const list: Dashboard[] = [
  {
    name: 'dashboard1',
    url:
      'xxx',
    uuid: 'xvlksdhjlfsdlf',
  },
  {
    name: 'dashboard2',
    url: 'https://reactjs.org/',
    uuid: 'xvlksdhjlfsfsdfdlf',
  },
];

const get = {
  data: {
    data: list,
  },
  status: 200,
};

export const post = {
  data: {
    data: undefined,
  },
  status: 201,
};

export default get;
