import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Tabs } from 'antd'
import { useTranslation } from 'react-i18next'
const Container = styled.div``

const ParamsContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #f7f8fa;
  border-radius: 4px;
  padding: 10px 0;
`

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
`

function Param(): ReactElement {
  const { t } = useTranslation()
  return (
    <ParamContainer>
      <div className="key">
        {Math.random() > 0.5 ? t('project_partner_name') : t('project_partner_url')}
      </div>
      <div className="value">猿辅导-教育部</div>
    </ParamContainer>
  )
}

function Params(): ReactElement {
  return (
    <ParamsContainer>
      <Param />
      <Param />
      <Param />
      <Param />
    </ParamsContainer>
  )
}

function WorkFlowTabs(): ReactElement {
  const { t } = useTranslation()
  return (
    <Tabs defaultActiveKey="1">
      <Tabs.TabPane tab={t('project_workflow')} key="1">
        Content of Tab Pane 1
      </Tabs.TabPane>
      <Tabs.TabPane tab={t('project_mix_dataset')} key="2">
        Content of Tab Pane 2
      </Tabs.TabPane>
      <Tabs.TabPane tab={t('project_model')} key="3">
        Content of Tab Pane 3
      </Tabs.TabPane>
      <Tabs.TabPane tab="API" key="4">
        Content of Tab Pane 4
      </Tabs.TabPane>
    </Tabs>
  )
}

function DetailBody(): ReactElement {
  return (
    <Container>
      <Params />
      <WorkFlowTabs />
    </Container>
  )
}

export default DetailBody
