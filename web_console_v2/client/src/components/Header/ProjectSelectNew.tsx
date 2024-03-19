import React, { FC, memo, useCallback, useEffect, useMemo, useState } from 'react';
import { useRecoilQuery } from 'hooks/recoil';
import { projectListQuery, projectState } from 'stores/project';
import { useRecoilState } from 'recoil';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { Select } from '@arco-design/web-react';
import { IconDown } from '@arco-design/web-react/icon';
import styled from 'styled-components';
import { useUrlState } from 'hooks';
import { Project } from 'typings/project';
import { useLocation } from 'react-router-dom';
const Option = Select.Option;

type Props = {
  isHidden?: boolean;
};

const StyledSelect = styled(Select)`
  max-width: 240px;
  .arco-select-view-value {
    color: white;
  }
  .arco-select-view-input {
    color: white;
  }
`;

interface IUrlState {
  project_id?: ID;
}

const ProjectSelectNew: FC<Props> = memo(({ isHidden }) => {
  const location = useLocation();
  const [urlState, setUrlState] = useUrlState<IUrlState>(
    { project_id: undefined },
    { navigateMode: 'replace' },
  );
  const [filterValue, setFilterValue] = useState<string>('');
  const projectsQuery = useRecoilQuery(projectListQuery);
  const [selectProject, setSelectProject] = useRecoilState(projectState);
  const projectList = useMemo(() => {
    const tempList = projectsQuery?.data?.filter((item) => item.name.indexOf(filterValue) !== -1);
    if (!filterValue) {
      return tempList;
    }
    return tempList.sort((a, b) => (a.name.length < b.name.length ? -1 : 1));
  }, [filterValue, projectsQuery]);

  const idNotExist = (id?: ID) => {
    return !id && id !== 0;
  };

  const refreshSelectProject = useCallback(
    (selectProject: Project | undefined) => {
      setSelectProject({ current: selectProject });
      store.set(LOCAL_STORAGE_KEYS.current_project, selectProject);
    },
    [setSelectProject],
  );

  const refreshUrl = useCallback(
    (project_id) => {
      setUrlState((pre) => ({
        ...pre,
        project_id: project_id,
      }));
    },
    [setUrlState],
  );

  const removeProject = () => {
    setSelectProject({ current: undefined });
    store.remove(LOCAL_STORAGE_KEYS.current_project);
  };

  useEffect(() => {
    const urlProjectIdExist = Boolean(urlState.project_id);
    const notMatch = Boolean(selectProject.current?.id !== parseInt(urlState.project_id));
    if (urlProjectIdExist && notMatch) {
      const selectProject = projectsQuery.data?.find((p) => p.id === parseInt(urlState.project_id));
      if (selectProject) {
        refreshSelectProject(selectProject);
      }
    } else {
      refreshUrl(selectProject.current?.id);
    }
    // watching location.pathname is necessary there for adding the project_id to the URL when switching pages
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectsQuery.data, location.pathname]);

  const handleOnChange = (projectId: ID) => {
    if (idNotExist(projectId)) {
      removeProject();
    } else {
      const selectProject = projectsQuery.data.find((p) => p.id === projectId);
      refreshSelectProject(selectProject);
    }
    refreshUrl(projectId);
  };

  if (projectsQuery.isLoading || !projectsQuery.data) {
    return <div style={{ gridArea: 'project-select' }} />;
  }

  return isHidden ? (
    <div className="empty" />
  ) : (
    <StyledSelect
      size={'small'}
      bordered={false}
      arrowIcon={<IconDown />}
      allowClear={true}
      value={selectProject.current?.id}
      placeholder={'请先选择工作区！'}
      showSearch={true}
      onChange={handleOnChange}
      filterOption={false}
      getPopupContainer={() => document.getElementById('page-header') as Element}
      onInputValueChange={(value) => {
        setFilterValue(value);
      }}
    >
      {projectList?.map((item) => {
        return (
          <Option key={item.id} value={item.id}>
            {item.name}
          </Option>
        );
      })}
    </StyledSelect>
  );
});

export default ProjectSelectNew;
