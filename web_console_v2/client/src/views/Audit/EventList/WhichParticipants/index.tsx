import React, { FC, useMemo } from 'react';

import { useRecoilQuery } from 'hooks/recoil';
import { projectListQuery } from 'stores/project';
import { participantListQuery } from 'stores/participant';
import MoreParticipants from '../MoreParticipants';

import { Spin } from '@arco-design/web-react';

type Props = {
  projectId?: ID;
  pureDomainName?: string;
  currentName?: string;
  currentDomainName?: string;
  loading?: boolean;
  showAll?: boolean;
  showCoordinator?: boolean;
};

const WhichParticipants: FC<Props> = ({
  projectId,
  pureDomainName,
  currentName,
  currentDomainName,
  loading,
  showAll = false,
  showCoordinator = false,
}) => {
  const { isLoading: projectLoading, data: projectList } = useRecoilQuery(projectListQuery);
  const { isLoading: participantsLoading, data: participantsList } = useRecoilQuery(
    participantListQuery,
  );

  const { currentCoordinatorName, currentCoordinatorDomainName } = useMemo(() => {
    const currentCoordinator = participantsList?.find(
      (item) => item.pure_domain_name === pureDomainName,
    );
    return {
      currentCoordinatorName: currentCoordinator?.name || '-',
      currentCoordinatorDomainName: currentCoordinator?.domain_name || '-',
    };
  }, [participantsList, pureDomainName]);

  const { collaboratorsName, collaboratorsDomain } = useMemo(() => {
    const currentParticipants =
      projectList?.find((item) => Number(item.id) === Number(projectId))?.participants || [];
    const collaborators = currentParticipants.filter(
      (item) => item.pure_domain_name !== pureDomainName,
    );
    const collaboratorsName = collaborators.map((item) => item.name);
    const collaboratorsDomain = collaborators.map((item) => ({
      name: item.name,
      domain_name: item.domain_name,
    }));
    return {
      collaboratorsName,
      collaboratorsDomain,
    };
  }, [projectList, pureDomainName, projectId]);

  if (loading || projectLoading || participantsLoading) {
    return <Spin />;
  }

  if (showCoordinator) {
    return showAll ? (
      <span>{`${currentCoordinatorName} | ${currentCoordinatorDomainName} `}</span>
    ) : (
      <span>{currentCoordinatorName}</span>
    );
  }

  return (
    <>
      {!showAll ? (
        <MoreParticipants
          textList={currentName ? [currentName, ...collaboratorsName] : collaboratorsName}
          count={1}
        />
      ) : collaboratorsDomain.length || currentName ? (
        <div>
          {currentName && <div> {`${currentName} | ${currentDomainName}`}</div>}
          {collaboratorsDomain.map((item) => (
            <div key={item.domain_name}>{`${item.name} | ${item.domain_name}`}</div>
          ))}
        </div>
      ) : (
        '-'
      )}
    </>
  );
};

export default WhichParticipants;
