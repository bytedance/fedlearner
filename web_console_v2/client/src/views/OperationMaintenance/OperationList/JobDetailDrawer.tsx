import React, { useMemo } from 'react';
import { Drawer, DrawerProps, Button, Message } from '@arco-design/web-react';
import { useQuery } from 'react-query';
import { fetchOperationDetail } from 'services/operation';
import CodeEditor from 'components/CodeEditor';
import { IconCopy } from '@arco-design/web-react/icon';
import { copyToClipboard, formatJSONValue } from 'shared/helpers';

import styles from './JobDetailDrawer.module.less';

const ContentHeight = '119px'; // 55(drawer header height) + 16*2(content padding) + 32(header height)

export interface Props {
  data?: string;
}

export interface Props extends DrawerProps {
  data?: string;
}

function JobDetailDrawer({ visible, data, title = '工作详情', ...restProps }: Props) {
  const jobInfo = useQuery(
    ['fetchOperationDetail', data],
    () => {
      if (data === '') return;
      return fetchOperationDetail({
        job_name: data || '',
      });
    },
    {
      retry: 0,
      cacheTime: 0,
      refetchOnWindowFocus: false,
    },
  );
  const job = useMemo(() => {
    if (!jobInfo.data) return 'this job_name is not exits';
    return JSON.stringify(jobInfo.data);
  }, [jobInfo]);

  function renderCodeEditorLayout() {
    return (
      <>
        <div className={styles.header_container}>
          <Button
            className={styles.copy_button}
            icon={<IconCopy />}
            onClick={onCopyClick}
            type="text"
          >
            复制
          </Button>
        </div>
        <CodeEditor
          language="json"
          isReadOnly={true}
          theme="grey"
          height={`calc(100vh - ${ContentHeight})`}
          value={formatJSONValue(job ?? '')}
        />
      </>
    );
  }

  return (
    <Drawer
      placement="right"
      title={title}
      closable={true}
      width="50%"
      visible={visible}
      unmountOnExit
      {...restProps}
    >
      <div className={styles.drawer_content}>{renderCodeEditorLayout()}</div>
    </Drawer>
  );

  function onCopyClick() {
    const isOK = copyToClipboard(formatJSONValue(job ?? ''));
    if (isOK) {
      Message.success('复制成功');
    } else {
      Message.error('复制失败');
    }
  }
}

export default JobDetailDrawer;
