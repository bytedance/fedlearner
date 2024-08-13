import React, { FC, useContext, useEffect, useState } from 'react';
import styled from './index.module.less';
import { useTranslation } from 'react-i18next';
import { JobExecutionDetalis } from 'typings/job';
import { Button } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import KibanaItem from './KibanaItem';
import GridRow from 'components/_base/GridRow';
import { giveWeakRandomKey } from 'shared/helpers';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';

type Props = {
  job: JobExecutionDetalis;
  isPeerSide?: boolean;
};

const JobKibanaMetrics: FC<Props> = ({ job }) => {
  const { t } = useTranslation();
  const [queryList, setQueryList] = useState([giveWeakRandomKey()]);

  const { isPeerSide, workflow } = useContext(JobExecutionDetailsContext);

  useEffect(() => {
    setQueryList([giveWeakRandomKey()]);
  }, [job?.id]);

  const isPeerMetricsPublic = (isPeerSide && workflow?.metric_is_public) || !isPeerSide;

  if (!isPeerMetricsPublic) {
    return (
      <div className={styled.metric_not_public}>{t('workflow.placeholder_metric_not_public')}</div>
    );
  }

  return (
    <section>
      {queryList.map((key) => (
        <KibanaItem key={key} />
      ))}

      <GridRow justify="center" top="20">
        <Button
          className={styled.add_chart_button}
          type="primary"
          icon={<IconPlus />}
          size="large"
          onClick={onAddClick}
        >
          {t('workflow.btn_add_kibana_chart')}
        </Button>
      </GridRow>
    </section>
  );

  function onAddClick() {
    const nextList = [...queryList, giveWeakRandomKey()];

    setQueryList(nextList);
  }
};

export default JobKibanaMetrics;
