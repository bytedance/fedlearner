import { message, Switch } from 'antd';
import React, { FC } from 'react';
import { useToggle } from 'react-use';
import { toggleWofklowForkable } from 'services/workflow';
import { to } from 'shared/helpers';
import { Workflow } from 'typings/workflow';

const ForkableSwitch: FC<{ workflow: Workflow; onSuccess: any }> = ({ workflow, onSuccess }) => {
  const [localForkable, toggleLocalForkable] = useToggle(false);
  const [useLocalState, toggleUseLocal] = useToggle(false);
  const [loading, toggle] = useToggle(false);
  return (
    <Switch
      checked={useLocalState ? localForkable : workflow.forkable}
      loading={loading}
      onChange={onForkableChange}
    />
  );

  async function onForkableChange(val: boolean) {
    toggle(true);
    const [res, error] = await to(toggleWofklowForkable(workflow.id, val));
    toggle(false);

    if (error) {
      toggleUseLocal(false);
      message.error(error.message);
      return;
    }

    toggleUseLocal(true);
    toggleLocalForkable(val);

    onSuccess(res);
  }
};

export default ForkableSwitch;
