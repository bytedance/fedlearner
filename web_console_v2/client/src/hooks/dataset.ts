import { useResetRecoilState } from 'recoil';
import { datasetBasicForm } from 'stores/dataset';

export function useResetCreateForm() {
  const resetBasicForm = useResetRecoilState(datasetBasicForm);

  return function () {
    resetBasicForm();
  };
}
