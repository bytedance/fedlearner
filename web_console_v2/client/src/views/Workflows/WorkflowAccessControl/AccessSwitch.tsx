import { Message, Switch } from '@arco-design/web-react';
import React, { FC } from 'react';
import { useToggle } from 'react-use';
import { to } from 'shared/helpers';
import { Workflow } from 'typings/workflow';

const AccessSwitch: FC<{
  workflow: Workflow;
  keyOfSource: keyof Workflow;
  onSuccess: any;
  patcher: (id: ID, val: boolean, projectId: ID) => any;
}> = ({ workflow, onSuccess, patcher, keyOfSource }) => {
  // Q: Why is there a copy of workflow.forkable locally
  // A: After the swicthing, there would be a noticable delay reflect the workflow.forkable change
  //    the local copy can reflect value change immediately before the server result coming
  const [localState, toggleLocalState] = useToggle(!!workflow[keyOfSource]);
  const [useLocalState, toggleUseLocal] = useToggle(false);
  const [loading, toggle] = useToggle(false);

  return (
    <Switch
      checked={useLocalState ? localState : !!workflow[keyOfSource]}
      loading={loading}
      onChange={onForkableChange}
    />
  );

  async function onForkableChange(val: boolean) {
    toggle(true);
    const [res, error] = await to(patcher(workflow.id, val, workflow.project_id));
    toggle(false);

    if (error) {
      toggleUseLocal(false);

      Message.error(error.message);
      return;
    }

    toggleUseLocal(true);

    toggleLocalState(val);

    onSuccess(res);
  }
};

export default AccessSwitch;
