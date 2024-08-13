import React, { FC } from 'react';
import { useHistory, useParams } from 'react-router';
import { Tag, Button, Message } from '@arco-design/web-react';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';
import { updateTrustedJob } from 'services/trustedCenter';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantList } from 'hooks';
import CONSTANTS from 'shared/constants';
import { AuthStatus } from 'typings/trustedCenter';
import { Avatar } from '../shared';
import './index.less';

const DatasetExportApplication: FC = () => {
  const projectId = useGetCurrentProjectId();
  const params = useParams<{ id: string; coordinator_id: string; name: string }>();
  const history = useHistory();
  const participantList = useGetCurrentProjectParticipantList();
  const participant = participantList.filter((item) => item?.id === Number(params.coordinator_id));
  const layoutTitle = <BackButton onClick={goBackTrustedCenter}>{'可信中心'}</BackButton>;

  return (
    <SharedPageLayout title={layoutTitle} centerTitle="数据集导出申请">
      <div className="dataset-application-container">
        <Avatar className="avatar" />
        <h3 className="title">{`「${params.name || CONSTANTS.EMPTY_PLACEHOLDER}」 的导出申请`}</h3>
        <div className="comment">
          {'该数据集为可信中心安全计算生成的计算结果，导出时需各合作伙伴审批通过'}
        </div>
        <div className="tag-container">
          <Tag color="arcoblue">{'发起方'}</Tag>
          <Tag style={{ marginLeft: '10px' }}>
            {participant?.[0]?.name || CONSTANTS.EMPTY_PLACEHOLDER}
          </Tag>
        </div>
        <div className="bottom">
          <Button className="bottom___button" onClick={onReject}>
            {'拒绝'}
          </Button>
          <Button className="bottom___button" type="primary" onClick={onPass}>
            {'通过'}
          </Button>
        </div>
      </div>
    </SharedPageLayout>
  );

  function goBackTrustedCenter() {
    history.push('/trusted-center');
  }

  async function onReject() {
    try {
      await updateTrustedJob(projectId!, params.id, {
        comment: '',
        auth_status: AuthStatus.WITHDRAW,
      });
      history.push('/trusted-center/dataset-application/rejected');
    } catch (error) {
      Message.error(error.message);
      return Promise.reject(error);
    }
  }

  async function onPass() {
    try {
      await updateTrustedJob(projectId!, params.id, {
        comment: '',
        auth_status: AuthStatus.AUTHORIZED,
      });
      history.push('/trusted-center/dataset-application/passed');
    } catch (error) {
      Message.error(error.message);
      return Promise.reject(error);
    }
  }
};

export default DatasetExportApplication;
