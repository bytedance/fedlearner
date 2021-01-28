import React, { FC } from 'react';
import {
  ConnectionStatus,
  getConnectionStatusClassName,
  getConnectionStatusTag,
} from 'typings/project';
import { useTranslation } from 'react-i18next';
import StateIndicator from 'components/StateIndicator';

interface Props {
  status: ConnectionStatus;
  tag?: boolean;
}

const ProjectConnectionStatus: FC<Props> = ({ status, tag }: Props) => {
  const { t } = useTranslation();

  return (
    <StateIndicator
      type={getConnectionStatusClassName(status)}
      text={t(getConnectionStatusTag(status))}
      tag={tag}
    />
  );
};

export default ProjectConnectionStatus;
