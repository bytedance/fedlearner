import React, { FC, useState } from 'react';
import FileExplorer from 'components/FileExplorer';
import { fetchDataSourceFileTreeList } from 'services/dataset';
import { useParams } from 'react-router';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { formatTimestamp } from 'shared/date';
import { CONSTANTS } from 'shared/constants';
import styled from './index.module.less';

type Props = {};

const PreviewFile: FC<Props> = () => {
  const { id } = useParams<{
    id: string;
    subtab: string;
  }>();
  const [updateAt, setUpdateAt] = useState(0);
  return (
    <div>
      <div className={styled.preview_update}>
        <IconInfoCircle />
        <span className={styled.preview_update_text}>
          最新更新时间 : {updateAt ? formatTimestamp(updateAt) : CONSTANTS.EMPTY_PLACEHOLDER}
        </span>
      </div>
      <FileExplorer
        isAsyncMode={true}
        isReadOnly={true}
        isShowNodeTooltip={false}
        isAutoSelectFirstFile={false}
        isExpandAll={false}
        getFileTreeList={getFileTreeList}
      />
    </div>
  );
  function getFileTreeList() {
    return fetchDataSourceFileTreeList(id).then((res) => {
      setUpdateAt(res.data.mtime);
      return res.data.files;
    });
  }
};

export default PreviewFile;
