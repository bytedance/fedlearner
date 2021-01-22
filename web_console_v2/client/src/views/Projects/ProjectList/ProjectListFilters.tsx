import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { Button, Input, Radio } from 'antd';
import { useTranslation } from 'react-i18next';
import { useHistory } from 'react-router-dom';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { DisplayType } from 'typings/component';

const Container = styled.div`
  height: 32px;
  display: flex;
  justify-content: space-between;
`;
const SearchInput = styled(Input.Search)`
  display: inline-block;
  width: 227px;
`;
const DisplaySelector = styled(Radio.Group)`
  display: inline-block;
  margin-left: 15px;
`;
const ProjectListDisplayOptions = [
  {
    labelKey: 'project.display_card',
    value: 1,
  },
  {
    labelKey: 'project.display_list',
    value: 2,
  },
];

interface Props {
  onDisplayTypeChange: (type: number) => void;
}

function Action({ onDisplayTypeChange }: Props): ReactElement {
  const { t } = useTranslation();
  const history = useHistory();

  return (
    <Container>
      <div>
        <Button
          type="primary"
          size="large"
          onClick={() => {
            history.push('/projects/create');
          }}
        >
          {t('project.create')}
        </Button>
      </div>
      <div>
        <SearchInput placeholder={t('project.search_placeholder')} />
        <DisplaySelector
          defaultValue={store.get(LOCAL_STORAGE_KEYS.projects_display) || DisplayType.Card}
          options={ProjectListDisplayOptions.map((i) => ({ label: t(i.labelKey), value: i.value }))}
          optionType="button"
          onChange={(e) => {
            onDisplayTypeChange(e.target.value);
          }}
        />
      </div>
    </Container>
  );
}

export default Action;
