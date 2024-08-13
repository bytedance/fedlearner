import React, { FC, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useHistory, useParams } from 'react-router';
import BackButton from 'components/BackButton';
import SharedPageLayout from 'components/SharedPageLayout';
import { Button, Result } from '@arco-design/web-react';
import './index.less';
import { useInterval } from 'react-use';

const REDIRECT_COUNTDOWN_DURATION = 5;
const ApplicationResult: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const [redirectCountdown, setRedirectCountdown] = useState(REDIRECT_COUNTDOWN_DURATION);
  const { result } = useParams<{ result: string }>();

  useInterval(() => {
    if (redirectCountdown === 0) {
      goBackTrustedCenter();
      return;
    }
    setRedirectCountdown(redirectCountdown - 1);
  }, 1000);

  const layoutTitle = (
    <BackButton onClick={goBackTrustedCenter}>
      {t('trusted_center.label_trusted_center')}
    </BackButton>
  );
  return (
    <SharedPageLayout title={layoutTitle} centerTitle="数据集导出申请">
      <div className="passed-container">
        <Result
          status={result === 'passed' ? 'success' : 'warning'}
          title={
            result === 'passed'
              ? t('trusted_center.title_passed')
              : t('trusted_center.title_rejected')
          }
          subTitle={t('trusted_center.title_status_tip', {
            second: redirectCountdown,
          })}
          extra={[
            <Button key="back" type="primary" onClick={goBackTrustedCenter}>
              {t('trusted_center.btn_go_back')}
            </Button>,
          ]}
        />
      </div>
    </SharedPageLayout>
  );

  function goBackTrustedCenter() {
    history.push('/trusted-center');
  }
};

export default ApplicationResult;
