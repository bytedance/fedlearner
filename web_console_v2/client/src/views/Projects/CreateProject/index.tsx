import React, { ReactElement } from 'react'
import BaseForm from '../BaseForm'
import styled from 'styled-components'
import { Breadcrumb } from 'antd'
import BreadcrumbSplit from 'components/Container/BreadcrumbSplit'
import { useHistory } from 'react-router-dom'
import { createProject } from 'services/project'
import { useTranslation } from 'react-i18next'

const Container = styled.div``

function CreateProject(): ReactElement {
  const history = useHistory()
  const { t } = useTranslation()
  return (
    <Container>
      <Breadcrumb separator={<BreadcrumbSplit />}>
        <Breadcrumb.Item
          onClick={() => {
            history.push('/projects')
          }}
        >
          {t('menu.label_project')}
        </Breadcrumb.Item>
        <Breadcrumb.Item>{t('project.create')}</Breadcrumb.Item>
      </Breadcrumb>

      <BaseForm onSubmit={onSubmit} />
    </Container>
  )
  async function onSubmit<CreateProjectFormData>(payload: CreateProjectFormData) {
    try {
      await createProject(payload)
    } catch (error) {
      throw error
    }
  }
}

export default CreateProject
