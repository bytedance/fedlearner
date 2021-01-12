import React, { ReactElement } from 'react';
import { getConnectionStatusClassName, getConnectionStatusTag } from 'typings/project';
import { useTranslation } from 'react-i18next';
import StateIndicator from 'components/StateIndicator';

interface ConnectionStatusProps {
  connectionStatus: number;
}

function ProjectConnectionStatus({ connectionStatus }: ConnectionStatusProps): ReactElement {
  const { t } = useTranslation();
  return (
    <StateIndicator
      type={getConnectionStatusClassName(connectionStatus)}
      text={t(getConnectionStatusTag(connectionStatus))}
    />
  );
}

export default ProjectConnectionStatus;
