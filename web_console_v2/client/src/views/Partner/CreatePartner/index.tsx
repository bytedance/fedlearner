import React, { FC } from 'react';
import PartnerForm from '../PartnerForm';
import { Message } from '@arco-design/web-react';
import { createParticipant } from 'services/participant';
import { useHistory } from 'react-router-dom';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';

import styles from './index.module.less';

const CreatePartner: FC = () => {
  const history = useHistory();

  return (
    <div className={styles.div_container}>
      <SharedPageLayout
        title={<BackButton onClick={() => history.goBack()}>合作伙伴列表</BackButton>}
        centerTitle="添加合作伙伴"
      >
        <PartnerForm isEdit={false} onSubmit={onSubmit} />
      </SharedPageLayout>
    </div>
  );

  async function onSubmit(payload: any) {
    try {
      await createParticipant(payload);
      Message.success('添加成功');
      history.push('/partners');
    } catch (error: any) {
      Message.error(error.message);
    }
  }
};

export default CreatePartner;
