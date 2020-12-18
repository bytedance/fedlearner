import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Pagination } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReactComponent as TrashCan } from 'assets/images/trash-can.svg'

const Container = styled.div`
  cursor: pointer;
`

interface Props {
  onClick: () => void
}

function RemoveField({ onClick }: Props): ReactElement {
  const { t } = useTranslation()
  return (
    <Container onClick={onClick}>
      <TrashCan />
    </Container>
  )
}

export default RemoveField
