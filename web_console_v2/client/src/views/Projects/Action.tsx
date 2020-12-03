import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Button, Input, Radio } from 'antd'
import { useTranslation } from 'react-i18next'
import { useHistory } from 'react-router-dom'

const Container = styled.div`
  margin: 18px 0;
  height: 32px;
  display: flex;
  justify-content: space-between;
`

const Right = styled.div``

const Left = styled.div``

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

const ProjectListDisplayOptions = [
  {
    labelKey: 'project.display_card',
    value: 1,
  },
  {
    labelKey: 'project.display_list',
    value: 2,
  },
]

interface Props {
  onDisplayTypeChange: (type: number) => void
}

function Action({ onDisplayTypeChange }: Props): ReactElement {
  const { t } = useTranslation()
  const history = useHistory()
  return (
    <Container>
      <Right>
        <CreateButton
          onClick={() => {
            history.push('/create-project')
          }}
        >
          {t('project.create')}
        </CreateButton>
      </Right>
      <Left>
        <SearchInput placeholder={t('project.search_placeholder')} />
        <DisplaySelector
          defaultValue={1}
          options={ProjectListDisplayOptions.map((i) => ({ label: t(i.labelKey), value: i.value }))}
          optionType="button"
          onChange={(e) => {
            onDisplayTypeChange(e.target.value)
          }}
        />
      </Left>
    </Container>
  )
}

export default Action
