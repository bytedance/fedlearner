import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { Tabs } from 'antd';
import { useTranslation } from 'react-i18next';
import { Project, Participant } from 'typings/project';

const Container = styled.div``;
const ParamsContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #f7f8fa;
  border-radius: 4px;
  padding: 10px 0;
`;
const ParamContainer = styled.div`
  height: 36px;
  display: flex;
  font-size: 13px;
  line-height: 36px;
  padding: 0 16px;
  .key {
    color: #707a8f;
    min-width: 104px;
  }
  .value {
    margin-left: 20px;
    color: #1a2233;
    flex: 1;
  }
`;
interface DetailBodyProps {
  project: Project;
}

interface ParamsProps {
  participants: Participant[];
  comment: string;
}

interface ParamProps {
  valueKey: string;
  value: string;
}

function Param({ valueKey, value }: ParamProps): ReactElement {
  const { t } = useTranslation();
  return (
    <ParamContainer>
      <div className="key">{t(geti18nKey(valueKey))}</div>
      <div className="value">{value}</div>
    </ParamContainer>
  );
  function geti18nKey(key: string): string {
    switch (key) {
      case 'name':
        return 'project.participant_name';
      case 'domain_name':
        return 'project.participant_domain';
      case 'url':
        return 'project.participant_url';
      case 'comment':
        return 'project.remarks';
      default:
        return null as never;
    }
  }
}

function Params({ participants, comment }: ParamsProps): ReactElement {
  return (
    <ParamsContainer>
      {Object.entries(participants[0]).map((i) => (
        <Param valueKey={i[0]} value={i[1]} key={i[1]} />
      ))}
      <Param valueKey="comment" value={comment} />
    </ParamsContainer>
  );
}

function WorkFlowTabs(): ReactElement {
  const { t } = useTranslation();
  return (
    <Tabs defaultActiveKey="1">
      <Tabs.TabPane tab={t('project.workflow')} key="1">
        Content of Tab Pane 1
      </Tabs.TabPane>
      <Tabs.TabPane tab={t('project.mix_dataset')} key="2">
        Content of Tab Pane 2
      </Tabs.TabPane>
      <Tabs.TabPane tab={t('project.model')} key="3">
        Content of Tab Pane 3
      </Tabs.TabPane>
      <Tabs.TabPane tab="API" key="4">
        Content of Tab Pane 4
      </Tabs.TabPane>
    </Tabs>
  );
}

function DetailBody({ project }: DetailBodyProps): ReactElement {
  return (
    <Container>
      <Params participants={project.config.participants} comment={project.comment} />
      <WorkFlowTabs />
    </Container>
  );
}

export default DetailBody;
