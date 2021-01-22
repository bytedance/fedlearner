import { cloneDeep } from 'lodash';
import { useSetRecoilState } from 'recoil';
import {
  workflowBasicForm,
  workflowJobsConfigForm,
  workflowTemplateForm,
  workflowInEditing,
  templateInUsing,
  DEFAULT_TEMPLATE_VALUES,
  DEFAULT_JOBS_CONFIG_VALUES,
  DEFAULT_BASIC_VALUES,
  peerConfigInPairing,
} from 'stores/workflow';

export function useResetCreateForms() {
  const setBasicForm = useSetRecoilState(workflowBasicForm);
  const setJobsConfigForm = useSetRecoilState(workflowJobsConfigForm);
  const setTemplateForm = useSetRecoilState(workflowTemplateForm);
  const setWorkflow = useSetRecoilState(workflowInEditing);
  const setWorkflowInUsing = useSetRecoilState(templateInUsing);
  const setpeerWorkflow = useSetRecoilState(peerConfigInPairing);

  return function () {
    setWorkflowInUsing(null as any);
    setWorkflow(null as any);
    setpeerWorkflow(null as any);
    setTemplateForm(cloneDeep(DEFAULT_TEMPLATE_VALUES));
    setJobsConfigForm(cloneDeep(DEFAULT_JOBS_CONFIG_VALUES));
    setBasicForm(cloneDeep(DEFAULT_BASIC_VALUES));
  };
}
