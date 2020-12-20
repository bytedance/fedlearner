import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Pagination } from 'antd'
import { useTranslation } from 'react-i18next'

const Container = styled.div`
  display: flex;
  width: 101px;
`

const TextStyle = styled.div`
  font-size: 13px;
  line-height: 28px;
  color: #424e66;
  margin-left: 8px;
`

interface Props {
  onClick: () => void
}

function AddField({ onClick }: Props): ReactElement {
  const { t } = useTranslation()
  return (
    <Container onClick={onClick}>
      <TextStyle>添加参数</TextStyle>
    </Container>
  )
}

export default AddField
