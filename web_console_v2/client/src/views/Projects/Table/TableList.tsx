import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Pagination } from 'antd'
import { useTranslation } from 'react-i18next'
import TableItem from './TableItem'

const Container = styled.div``

function TableList(): ReactElement {
  return (
    <Container>
      <TableItem />
    </Container>
  )
}

export default TableList
