import { useResetRecoilState } from 'recoil';
import { templateForm } from 'stores/template';

export function useResetCreateForm() {
  const resetForm = useResetRecoilState(templateForm);

  return function () {
    resetForm();
  };
}
