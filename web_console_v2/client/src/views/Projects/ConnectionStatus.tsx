import React, { ReactElement } from 'react'
import styled from 'styled-components'
import classNames from 'classnames'
import { getConnectionStatusClassName, getConnectionStatusTag } from 'typings/project'
import { useTranslation } from 'react-i18next'

const Container = styled.div`
  .project-connection-status {
    font-size: 13px;
    line-height: 22px;
    color: var(--textColor);
    &.success {
      &::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 4px;
        background-color: var(--successGreen);
        margin-right: 8px;
      }
    }
    &.waiting {
      &::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 4px;
        background-color: var(--orange6);
        margin-right: 8px;
      }
    }
    &.failed {
      &::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 4px;
        background-color: var(--failedRed);
        margin-right: 8px;
      }
    }
    &.checking {
      &::before {
        content: '';
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 4px;
        background-color: var(--primaryColor);
        margin-right: 8px;
      }
    }
  }
`

interface ConnectionStatusProps {
  connectionStatus: number
}

function ProjectConnectionStatus({ connectionStatus }: ConnectionStatusProps): ReactElement {
  const { t } = useTranslation()
  return (
    <Container>
      <div
        className={classNames({
          'project-connection-status': true,
          [getConnectionStatusClassName(connectionStatus)]: true,
        })}
      >
        {t(getConnectionStatusTag(connectionStatus))}
      </div>
    </Container>
  )
}

export default ProjectConnectionStatus
