import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import { Button, Input, Radio, Modal } from 'antd'
import { useTranslation } from 'react-i18next'
import BaseForm from './BaseForm'

const Container = styled.div`
  margin: 18px 0;
  height: 32px;
  display: flex;
  justify-content: space-between;
`

const Right = styled.div`

`

const Left = styled.div`

`

const CreateButton = styled(Button)`
  display: inline-block;
  background-color: var(--primaryColor);
  color: white;
  font-weight: 500;
  font-size: 13px;
  line-height: 22px;
`

const SearchInput = styled(Input.Search)`
   display: inline-block;
   width: 227px;
`

const DisplaySelector = styled(Radio.Group)`
  display: inline-block;
  margin-left: 15px;
`

function Action(): ReactElement {
  const { t } = useTranslation()

  const ProjectListDisplayOptions = [
    {
      label: t('project_display_card'),
      value: 1,
    },
    {
      label: t('project_display_list'),
      value: 2,
    }
  ]

  const [isModalVisible, setIsModalVisible] = useState(false);
  return (
    <Container>
      <Right>
        <CreateButton onClick={()=>setIsModalVisible(true)}>{t('project_create')}</CreateButton>
      </Right>
      <Left>
        <SearchInput placeholder={t('project_search_placeholder')}/>
        <DisplaySelector options={ProjectListDisplayOptions} optionType="button" />
      </Left>
      <Modal
        title="新建项目"
        visible={isModalVisible}
        onOk={createProject}
        onCancel={()=>setIsModalVisible(false)}
        width={400}
        zIndex={2000}
      >
        <BaseForm />
      </Modal>
    </Container>
  )
}

async function createProject() {
  console.log('create')
}

export default Action
