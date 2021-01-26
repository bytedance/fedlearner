import { atom } from 'recoil';
import { DatasetCreatePayload, DatasetType } from 'typings/dataset';

export const DEFAULT_BASIC_VALUES = {
  name: '',
  dataset_type: DatasetType.PSI,
  comment: '',
};
export const datasetBasicForm = atom<DatasetCreatePayload>({
  key: 'DatasetBasicForm',
  default: DEFAULT_BASIC_VALUES,
});
