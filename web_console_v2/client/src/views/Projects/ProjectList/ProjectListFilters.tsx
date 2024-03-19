import React, { ReactElement } from 'react';
import { Input, Radio } from '@arco-design/web-react';
import { IconApps, IconList } from '@arco-design/web-react/icon';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { DisplayType } from 'typings/component';
import { ProjectListType } from 'typings/project';

import styles from './index.module.less';

const ProjectListDisplayOptions = [
  {
    label: <IconApps />,
    value: 1,
  },
  {
    label: <IconList />,
    value: 2,
  },
];

const ProjectListTypeOptions = [
  {
    label: '可用工作区',
    value: 'complete',
  },
  {
    label: '待授权工作区',
    value: 'pending',
  },
];

interface Props {
  onDisplayTypeChange: (type: number) => void;
  onProjectListTypeChange?: (type: ProjectListType) => void;
  onSearch: (value: string) => void;
  onChange?: (value: string) => void;
  defaultSearchText?: string;
  searchText?: string;
  projectListType: ProjectListType;
}

function Action({
  onDisplayTypeChange,
  onProjectListTypeChange,
  onSearch,
  onChange,
  defaultSearchText,
  projectListType,
}: Props): ReactElement {
  return (
    <div className={styles.list_filter_container}>
      <div>
        <Radio.Group
          defaultValue={projectListType ?? ProjectListType.COMPLETE}
          options={ProjectListTypeOptions}
          type="button"
          onChange={(value) => {
            onProjectListTypeChange?.(value);
          }}
        />
      </div>
      <div>
        <Input.Search
          className={`custom-input ${styles.filter_content_input}`}
          placeholder={'输入工作区名称关键词搜索'}
          onSearch={onSearch}
          defaultValue={defaultSearchText || undefined}
          onChange={(value) => {
            onChange?.(value);
          }}
          allowClear
        />
        <Radio.Group
          className={`custom-radio ${styles.filter_content_radio}`}
          defaultValue={store.get(LOCAL_STORAGE_KEYS.projects_display) || DisplayType.Card}
          options={ProjectListDisplayOptions}
          type="button"
          onChange={(value) => {
            onDisplayTypeChange(value);
          }}
        />
      </div>
    </div>
  );
}

export default Action;
