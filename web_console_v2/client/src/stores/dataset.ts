import { atom } from 'recoil';
import { DatasetCreatePayload, DatasetType } from 'typings/dataset';

export const datasetBasicForm = atom<DatasetCreatePayload>({
  key: 'DatasetBasicForm',
  default: {
    name: '',
    dataset_type: DatasetType.PSI,
    comment: '',
  },
});
