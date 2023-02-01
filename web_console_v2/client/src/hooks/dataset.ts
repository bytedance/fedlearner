import { useResetRecoilState, useSetRecoilState } from 'recoil';
import { datasetBasicForm, forceReloadDatasetList } from 'stores/dataset';

export function useResetCreateForm() {
  const resetBasicForm = useResetRecoilState(datasetBasicForm);

  return function () {
    resetBasicForm();
  };
}

export function useReloadDatasetList() {
  const setter = useSetRecoilState(forceReloadDatasetList);

  return function () {
    setter(Math.random());
  };
}
