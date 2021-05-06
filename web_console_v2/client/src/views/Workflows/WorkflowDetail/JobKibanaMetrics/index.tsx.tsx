import React, { FC, useEffect, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { JobExecutionDetalis } from 'typings/job';
import { Button } from 'antd';
import { Plus } from 'components/IconPark';
import KibanaItem from './KibanaItem';
import GridRow from 'components/_base/GridRow';
import { giveWeakRandomKey } from 'shared/helpers';

const Container = styled.div``;
const ChartContainer = styled.div`
  margin-bottom: 20px;
`;

const AddChartButton = styled(Button)`
  width: 250px;
`;

type Props = {
  job: JobExecutionDetalis;
  isPeerSide?: boolean;
};

const JobKibanaMetrics: FC<Props> = ({ job }) => {
  const { t } = useTranslation();
  const [chartList, setChartList] = useState([giveWeakRandomKey()]);

  useEffect(() => {
    setChartList([giveWeakRandomKey()]);
  }, [job?.id]);

  return (
    <Container>
      {chartList.map((key) => (
        <ChartContainer key={key}>
          <KibanaItem />
        </ChartContainer>
      ))}

      <GridRow justify="center">
        <AddChartButton type="primary" icon={<Plus />} size="large" onClick={onAddClick}>
          {t('workflow.btn_add_kibana_chart')}
        </AddChartButton>
      </GridRow>
    </Container>
  );

  function onAddClick() {
    const nextList = [...chartList, giveWeakRandomKey()];

    setChartList(nextList);
  }
};

export default JobKibanaMetrics;
