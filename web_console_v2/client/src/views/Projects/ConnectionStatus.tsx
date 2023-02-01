import React, { ForwardRefRenderFunction, useImperativeHandle, forwardRef } from 'react';
import {
  ConnectionStatus,
  getConnectionStatusClassName,
  getConnectionStatusTag,
  Project,
} from 'typings/project';
import StateIndicator from 'components/StateIndicator';
import { useCheckConnection } from 'hooks/project';
import { TIME_INTERVAL } from 'shared/constants';

export interface Props {
  status?: ConnectionStatus;
  tag?: boolean;
  project: Project;
}

export interface ExposedRef {
  checkConnection: Function;
}

const ProjectConnectionStatus: ForwardRefRenderFunction<ExposedRef, Props> = (
  { status, tag, project },
  parentRef,
) => {
  const [innerStatus, checkConnection] = useCheckConnection(project, {
    refetchOnWindowFocus: false,
    refetchInterval: TIME_INTERVAL.CONNECTION_CHECK,
    enabled: !status,
  });

  useImperativeHandle(parentRef, () => {
    return {
      checkConnection,
    };
  });

  return (
    <StateIndicator
      type={getConnectionStatusClassName(innerStatus)}
      text={getConnectionStatusTag(innerStatus)}
      tag={tag}
    />
  );
};

export default forwardRef(ProjectConnectionStatus);
