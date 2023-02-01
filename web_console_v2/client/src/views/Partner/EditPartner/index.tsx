import React, { FC, useMemo } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import { Message } from '@arco-design/web-react';
import PartnerForm from '../PartnerForm';
import { getParticipantDetailById, updateParticipant } from 'services/participant';
import { useQuery } from 'react-query';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

import styles from './index.module.less';

const EditPartner: FC = () => {
  const history = useHistory();
  const { id: partnerId } = useParams<{
    id: string;
  }>();

  const { data: participantQuery, isLoading, isError, error } = useQuery(
    ['getParticipantDetail', partnerId],
    () => getParticipantDetailById(partnerId),
    {
      cacheTime: 0,
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
    history.push('/partners');
  }

  const dataProps = useMemo(() => {
    if (!isLoading && participantQuery?.data) {
      return { data: participantQuery?.data };
    }
    return {};
  }, [isLoading, participantQuery?.data]);

  return (
    <div className={styles.div_container}>
      <SharedPageLayout
        title={<BackButton onClick={() => history.goBack()}>合作伙伴列表</BackButton>}
        centerTitle="变更合作伙伴"
      >
        <PartnerForm isEdit={true} {...dataProps} onSubmit={onSubmit} />
      </SharedPageLayout>
    </div>
  );

  async function onSubmit(payload: any) {
    try {
      // If there is no modification, no request will be sent
      if (Object.keys(payload).length) {
        await updateParticipant(partnerId, payload);
      }
      Message.success('变更合作伙伴成功！');
      history.push('/partners');
    } catch (error: any) {
      Message.error(error.message);
    }
  }
};

export default EditPartner;
