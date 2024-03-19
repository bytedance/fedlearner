import React from 'react';
import { ModelJob } from 'typings/modelCenter';
import { useGetCurrentProjectParticipantName } from 'hooks';

const WhichRole: React.FC<{ job?: ModelJob }> = ({ job }) => {
  const participantName = useGetCurrentProjectParticipantName();
  if (!job) {
    return null;
  }
  return <span>{job.role === 'PARTICIPANT' ? participantName : '本方'}</span>;
};

export default WhichRole;
