import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Pagination } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReactComponent as Add } from 'assets/images/add.svg'

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

const AddContainer = styled.div`
  background-color: var(--arcoblue6);
  height: 28px;
  width: 28px;
  border-radius: 2px;
  padding-top: 4px;
  padding-left: 9px;
`

interface Props {
  onClick: () => void
}

function AddField({ onClick }: Props): ReactElement {
  const { t } = useTranslation()
  return (
    <Container onClick={onClick}>
      <AddContainer>
        <Add />
      </AddContainer>
      <TextStyle>添加参数</TextStyle>
    </Container>
  )
}

export default AddField
