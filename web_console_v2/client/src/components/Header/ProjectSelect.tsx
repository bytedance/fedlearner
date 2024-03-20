import React, { FC, memo } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Dropdown } from 'antd';
import PrettyMenu, { PrettyMenuItem } from 'components/PrettyMenu';
import { useRecoilQuery } from 'hooks/recoil';
import { projectListQuery, projectState } from 'stores/project';
import GridRow from 'components/_base/GridRow';
import { useRecoilState } from 'recoil';
import { CaretDown } from 'components/IconPark';
import { CloseCircleFilled } from '@ant-design/icons';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { Project } from 'typings/project';

const Trigger = styled(GridRow)`
  grid-area: project-select;
  font-size: 14px;
  cursor: pointer;

  &:hover {
    > [data-name='clear'] {
      display: block;
    }

    > [data-name='arrow']:not([data-project-selected='false']) {
      display: none;
    }
  }
`;
const Placeholder = styled.small`
  opacity: 0.4;
`;
const ProjectItem = styled.div`
  cursor: pointer;
`;
const ClearButton = styled(CloseCircleFilled)`
  display: none;
  font-size: 12px;
`;

const ProjectSelect: FC = memo(() => {
  const { t } = useTranslation();

  const projectsQuery = useRecoilQuery(projectListQuery);
  const [state, setProjectState] = useRecoilState(projectState);

  if (projectsQuery.isLoading || !projectsQuery.data) {
    return <Trigger />;
  }

  const hasProjectSelected = Boolean(state.current);

  return (
    <Dropdown
      trigger={['click']}
      overlay={
        <PrettyMenu>
          {projectsQuery.data?.map((item, index) => (
            <PrettyMenuItem key={item.id + index} onClick={() => onProjectSelect(item)}>
              <ProjectItem>
                <div>{item.name}</div>
              </ProjectItem>
            </PrettyMenuItem>
          ))}
          {projectsQuery.data?.length === 0 && t('project.placeholder_no_project')}
        </PrettyMenu>
      }
      placement="bottomCenter"
    >
      <Trigger gap={5} left="20">
        {state.current ? (
          <GridRow gap="4">{state.current.name}</GridRow>
        ) : (
          <Placeholder>{t('project.placeholder_global_project_filter')}</Placeholder>
        )}
        {hasProjectSelected && <ClearButton data-name="clear" onClick={onClearCick} />}
        <CaretDown
          data-project-selected={hasProjectSelected}
          data-name="arrow"
          style={{ fontSize: 12 }}
        />
      </Trigger>
    </Dropdown>
  );

  function onClearCick(evt: React.MouseEvent) {
    evt.stopPropagation();
    setProjectState({ current: undefined });
    store.remove(LOCAL_STORAGE_KEYS.current_project);
  }
  function onProjectSelect(item: Project) {
    setProjectState({ current: item });
    store.set(LOCAL_STORAGE_KEYS.current_project, item);
  }
});

export default ProjectSelect;
