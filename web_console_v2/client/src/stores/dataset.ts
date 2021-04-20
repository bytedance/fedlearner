import { atom } from 'recoil';
import { DatasetCreatePayload, DatasetType } from 'typings/dataset';

export const datasetBasicForm = atom<DatasetCreatePayload>({
  key: 'DatasetBasicForm',
  default: {
    name: '',
    project_id: (undefined as unknown) as ID,
    dataset_type: DatasetType.PSI,
    comment: '',
  },
});
