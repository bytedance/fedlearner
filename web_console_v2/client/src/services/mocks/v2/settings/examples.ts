import { SystemVariable } from 'typings/settings';

export const fixed: SystemVariable = {
  name: 'fixed',
  value: 'testval',
  value_type: 'STRING',
  fixed: true,
};

export const noFixed: SystemVariable = {
  name: 'noFixed',
  value: 'test val',
  value_type: 'STRING',
  fixed: false,
};

export const int: SystemVariable = {
  name: 'int',
  value: 1,
  value_type: 'INT',
  fixed: false,
};

export const string: SystemVariable = {
  name: 'string',
  value: 'string val',
  value_type: 'STRING',
  fixed: false,
};

export const emptyObject: SystemVariable = {
  name: 'emptyObject',
  value: {},
  value_type: 'OBJECT',
  fixed: false,
};
export const object: SystemVariable = {
  name: 'object',
  value: { a: 1, b: 2, c: 3, d: { e: 4 } },
  value_type: 'OBJECT',
  fixed: false,
};
export const emptyList: SystemVariable = {
  name: 'emptyList',
  value: [],
  value_type: 'LIST',
  fixed: false,
};
export const list: SystemVariable = {
  name: 'list',
  value: [{ a: 1 }, { a: 2 }, { a: 3 }],
  value_type: 'LIST',
  fixed: false,
};

export const variables: SystemVariable[] = [
  int,
  string,
  fixed,
  noFixed,
  emptyObject,
  object,
  emptyList,
  list,
];
