import React, { FC, useContext, useEffect, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { JobExecutionDetalis } from 'typings/job';
import { Button } from 'antd';
import { Plus } from 'components/IconPark';
import KibanaItem from './KibanaItem';
import GridRow from 'components/_base/GridRow';
import { giveWeakRandomKey } from 'shared/helpers';
import { MixinFlexAlignCenter } from 'styles/mixins';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';

const AddChartButton = styled(Button)`
  width: 250px;
`;
const MetricsNotPublic = styled.div`
  ${MixinFlexAlignCenter()}
  display: flex;
  height: 160px;
  font-size: 12px;
  color: var(--textColorSecondary);
`;

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

  const isPeerMetricsPublic = isPeerSide && workflow?.metric_is_public;

  if (!isPeerMetricsPublic) {
    return <MetricsNotPublic>{t('workflow.placeholder_metric_not_public')}</MetricsNotPublic>;
  }

  return (
    <section>
      {queryList.map((key) => (
        <KibanaItem key={key} />
      ))}

      <GridRow justify="center" top="20">
        <AddChartButton type="primary" icon={<Plus />} size="large" onClick={onAddClick}>
          {t('workflow.btn_add_kibana_chart')}
        </AddChartButton>
      </GridRow>
    </section>
  );

  function onAddClick() {
    const nextList = [...queryList, giveWeakRandomKey()];

    setQueryList(nextList);
  }
};

export default JobKibanaMetrics;
