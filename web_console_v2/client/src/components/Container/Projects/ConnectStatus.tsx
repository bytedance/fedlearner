import React, { ReactElement } from 'react'
import styled from 'styled-components'
import classNames from 'classnames'
import { getConnectStatusClassName, getConnectStatusTag } from 'typings/enum'
import { useTranslation } from 'react-i18next'

const Container = styled.div`
  .project-connect-status {
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

interface ConnectStatusProps {
  connectStatus: number
}

function ConnectStatus(props: ConnectStatusProps): ReactElement {
  const { t } = useTranslation()
  return (
    <Container>
      <div
        className={classNames({
          'project-connect-status': true,
          [getConnectStatusClassName(props.connectStatus)]: true,
        })}
      >
        {t(getConnectStatusTag(props.connectStatus))}
      </div>
    </Container>
  )
}

export default ConnectStatus
