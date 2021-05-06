import React, { FC, useContext, useEffect, useState } from 'react';
import styled from 'styled-components';
import KibanaParamsForm from './KibanaParamsForm';
import KibanaEmbeddedChart from './KibanaEmbeddedChart';
import { Col, message, Row } from 'antd';
import { JobType } from 'typings/job';
import { fetchJobEmbedKibanaSrc } from 'services/workflow';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';
import { to } from 'shared/helpers';
import { KibanaQueryParams } from 'typings/kibana';
import { useToggle } from 'react-use';
import { useTranslation } from 'react-i18next';

const Container = styled.div`
  position: relative;
  padding: 20px 20px 10px;
  border: 1px solid var(--lineColor);
  border-radius: 4px;
`;

const KibanaItem: FC = () => {
  /** Need a empty string as placeholder on left side */
  const { t } = useTranslation();
  const [embedSrcs, setEmbedSrcs] = useState(['']);
  const [configuring, toggleConfiguring] = useToggle(true);

  const context = useContext(JobExecutionDetailsContext);

  useEffect(() => {
    setEmbedSrcs(['']);
    toggleConfiguring(true);
  }, [context.job?.id, toggleConfiguring]);

  return (
    <Container>
      <Row gutter={20}>
        <Col span={configuring ? 12 : 24}>
          {embedSrcs.map((src) => (
            <KibanaEmbeddedChart
              src={`${src}`}
              fill={!configuring}
              onEditParams={onEditParamsClick}
              onOpenNewWindow={onNewWindowClick}
            />
          ))}
        </Col>

        {configuring && (
          <Col span={12}>
            <KibanaParamsForm
              jobType={JobType.DATA_JOIN}
              onConfirm={onConfirm}
              onNewWindowPreview={onNewWindowPreview}
              onPreview={onPreview}
            />
          </Col>
        )}
      </Row>
    </Container>
  );

  async function fetchSrc(values: KibanaQueryParams): Promise<string[]> {
    const [res, err] = await to(fetchJobEmbedKibanaSrc(context.job.id, values));
    if (err) {
      return message.error(err.message);
    }

    if (res.data.length) {
      return res.data;
    }

    message.warn(t('workflow.msg_no_available_kibana'));

    return [''];
  }

  async function onConfirm(values: KibanaQueryParams) {
    const srcs = await fetchSrc(values);
    setEmbedSrcs(srcs);
    toggleConfiguring(false);
  }
  async function onNewWindowPreview(values: KibanaQueryParams) {
    const srcs = await fetchSrc(values);

    srcs.forEach(async (src) => {
      window.open(src, '_blank noopener');
    });
  }
  async function onPreview(values: KibanaQueryParams) {
    const src = await fetchSrc(values);
    setEmbedSrcs(src);
  }
  function onEditParamsClick() {
    toggleConfiguring(true);
  }
  function onNewWindowClick(src: string) {
    if (src) {
      window.open(src, '_blank noopener');
    }
  }
};

export default KibanaItem;
