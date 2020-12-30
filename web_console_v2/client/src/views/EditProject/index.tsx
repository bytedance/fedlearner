import React, { ReactElement } from 'react'
import BaseForm from 'components/Container/BaseForm'
import styled from 'styled-components'
import { Breadcrumb } from 'antd'
import BreadcrumbSplit from 'components/Container/BreadcrumbSplit'
import { useHistory } from 'react-router-dom'
import { updateProject } from 'services/project'
import { useTranslation } from 'react-i18next'
import { CertificateConfigType } from 'typings/enum'

const Container = styled.div``

function CreateProject(props: any): ReactElement {
  const history = useHistory()
  const { t } = useTranslation()
  const project: Project = props?.location?.state?.project

  if (!project) history.push('/projects')

  const initialValues: FormInitialValues = {
    certificateConfigType: CertificateConfigType.BackendConfig,
    name: project.name,
    participantName: project.config.participants[0].name,
    participantUrl: project.config.participants[0].url,
    participantDomainName: project.config.participants[0].domain_name,
    comment: project.comment,
    variables: project.config.variables || [],
  }
  return (
    <Container>
      <Breadcrumb separator={<BreadcrumbSplit />}>
        <Breadcrumb.Item
          onClick={() => {
            history.push('/projects')
          }}
        >
          {t('menu_label_project')}
        </Breadcrumb.Item>
        <Breadcrumb.Item>{t('project.edit')}</Breadcrumb.Item>
      </Breadcrumb>
      <BaseForm onSubmit={onSubmit} edit initialValues={initialValues} />
    </Container>
  )
  async function onSubmit<UpdateProjectFormData>(payload: UpdateProjectFormData) {
    try {
      await updateProject(project.id, payload)
    } catch (error) {
      throw error
    }
  }
}

export default CreateProject
