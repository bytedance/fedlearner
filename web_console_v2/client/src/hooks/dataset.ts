import { cloneDeep } from 'lodash';
import { useSetRecoilState } from 'recoil';
import { datasetBasicForm, DEFAULT_BASIC_VALUES } from 'stores/dataset';

export function useResetCreateForm() {
  const setBasicForm = useSetRecoilState(datasetBasicForm);

  return function () {
    setBasicForm(cloneDeep(DEFAULT_BASIC_VALUES));
  };
}
