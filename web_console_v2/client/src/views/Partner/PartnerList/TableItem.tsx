import React, { FC } from 'react';
import { ConnectionStatusType, Participant } from 'typings/participant';
import { useHistory } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { participantConnectionState } from 'stores/participant';
import MoreActions from 'components/MoreActions';
import { CONSTANTS } from 'shared/constants';

export const VersionItem: FC<{ partnerId: ID }> = ({ partnerId: id }) => {
  const connectionStatus = useRecoilValue(participantConnectionState(id));
  return (
    <span>
      {connectionStatus.application_version?.version ||
        connectionStatus.application_version?.revision?.slice(-6) ||
        CONSTANTS.EMPTY_PLACEHOLDER}
    </span>
  );
};

export const ActionItem: FC<{ data: Participant; onDelete: () => void }> = ({ data, onDelete }) => {
  const history = useHistory();
  const connectionStatus = useRecoilValue(participantConnectionState(data.id));

  const isProcessing = connectionStatus.success === ConnectionStatusType.Processing;
  const isHaveLinkedProject = !!data.num_project;

  return (
    <MoreActions
      actionList={[
        {
          label: '删除',
          onClick: onDelete,
          disabled: isProcessing || isHaveLinkedProject,
          disabledTip: isProcessing ? '连接中不可删除' : '需解除合作伙伴所有关联工作区才可删除',
          danger: true,
        },
        {
          label: '变更',
          onClick: () => {
            history.push(`/partners/edit/${data.id}`);
          },
          disabled: isProcessing,
          disabledTip: isProcessing
            ? '连接中不可变更'
            : '需解除合作伙伴所有关联工作区且连接失败时才可变更',
        },
      ]}
    />
  );
};
