import React, { useState, useEffect } from 'react';

import { formatTimestamp } from 'shared/date';
import { copyToClipboard, formatJSONValue } from 'shared/helpers';
import { CONSTANTS } from 'shared/constants';
import { systemInfoQuery } from 'stores/app';
import { useRecoilQuery } from 'hooks/recoil';

import { Drawer, Button, Message, Tag } from '@arco-design/web-react';
import { IconCopy } from '@arco-design/web-react/icon';
import { LabelStrong } from 'styles/elements';
import CodeEditor from 'components/CodeEditor';
import BackButton from 'components/BackButton';

import PropList from '../PropList';

import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { Audit, EventType } from 'typings/audit';

import styles from './index.module.less';
import WhichParticipants from '../WhichParticipants';

export interface Props extends DrawerProps {
  data?: Audit;
  event_type: EventType;
}

const hideExtraBlockList = ['null', '{}'];

function EventDetailDrawer({ visible, data, title = '事件详情', event_type, ...restProps }: Props) {
  const [isShowCodeEditor, setIsShowCodeEditor] = useState(false);
  const { data: systemInfo } = useRecoilQuery(systemInfoQuery);
  const { name: myName, domain_name: myDomainName, pure_domain_name: myPureDomainName } =
    systemInfo || {};

  useEffect(() => {
    if (!visible) {
      // reset isShowCodeEditor
      setIsShowCodeEditor((prevState) => false);
    }
  }, [visible]);

  function renderInfoLayout() {
    return (
      <>
        <LabelStrong isBlock={true}>基础信息</LabelStrong>
        <PropList
          list={[
            {
              key: '事件ID',
              value: data?.uuid ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '事件时间',
              value: data?.created_at
                ? formatTimestamp(data.created_at)
                : CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '事件名称',
              value: data?.name ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '用户名',
              value: data?.user?.username ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '操作名称',
              value: data?.op_type ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
          ]}
        />
        <div className={styles.gap} />
        <LabelStrong isBlock={true}>请求信息</LabelStrong>
        <PropList
          list={[
            {
              key: '请求ID',
              value: data?.uuid ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: 'AccessKey ID',
              value: data?.access_key_id ?? CONSTANTS.EMPTY_PLACEHOLDER,
              isCanCopy: true,
            },
            {
              key: '事件结果',
              value: data?.result ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '错误码',
              value: data?.error_code ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '资源类型',
              value: data?.resource_type ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '资源名称',
              value: data?.resource_name ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '源IP地址',
              value: data?.source_ip ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '额外信息',
              value:
                data?.extra && !hideExtraBlockList.includes(data.extra) ? (
                  <span className={styles.click_text}>查看</span>
                ) : (
                  CONSTANTS.EMPTY_PLACEHOLDER
                ),
              onClick: () => {
                if (data?.extra && !hideExtraBlockList.includes(data.extra)) {
                  setIsShowCodeEditor(true);
                }
              },
            },
          ]}
        />
      </>
    );
  }
  function renderCrossDomainInfoLayout() {
    return (
      <>
        <LabelStrong isBlock={true}>基础信息</LabelStrong>
        <PropList
          list={[
            {
              key: '事件ID',
              value: data?.uuid ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '事件时间',
              value: data?.created_at
                ? formatTimestamp(data.created_at)
                : CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '事件名称',
              value: data?.name ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '操作名称',
              value: data?.op_type ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
          ]}
        />
        <div className={styles.gap} />
        <LabelStrong isBlock={true}>请求信息</LabelStrong>
        <PropList
          list={[
            {
              key: '请求ID',
              value: data?.uuid ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '事件结果',
              value: data?.result ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '资源类型',
              value: data?.resource_type ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
            {
              key: '资源名称',
              value: data?.resource_name ?? CONSTANTS.EMPTY_PLACEHOLDER,
            },
          ]}
        />
        <div className={styles.gap} />
        <LabelStrong isBlock={true}>跨域信息</LabelStrong>
        <PropList
          list={[
            {
              key: '发起方',
              value:
                data?.coordinator_pure_domain_name === myPureDomainName ? (
                  <span>
                    {`${myName} | ${myDomainName}`} <Tag color="arcoblue"> 本侧</Tag>
                  </span>
                ) : (
                  <WhichParticipants
                    pureDomainName={data?.coordinator_pure_domain_name}
                    showCoordinator={true}
                    showAll={true}
                  />
                ),
            },
            {
              key: '协作方',
              value: (
                <WhichParticipants
                  currentDomainName={
                    data?.coordinator_pure_domain_name !== myPureDomainName
                      ? myDomainName
                      : undefined
                  }
                  currentName={
                    data?.coordinator_pure_domain_name !== myPureDomainName ? myName : undefined
                  }
                  pureDomainName={data?.coordinator_pure_domain_name}
                  projectId={data?.project_id}
                  showAll={true}
                />
              ),
            },
          ]}
        />
      </>
    );
  }
  function renderCodeEditorLayout() {
    return (
      <>
        <div className={styles.header}>
          <BackButton onClick={onBackClick}> 返回</BackButton>
          <Button
            className={styles.styled_copy_button}
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
          height="calc(100vh - 119px)" // 55(drawer header height) + 16*2(content padding) + 32(header height)
          value={formatJSONValue(data?.extra ?? '')}
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
      <div className={styles.content}>
        {isShowCodeEditor
          ? renderCodeEditorLayout()
          : event_type === EventType.CROSS_DOMAIN
          ? renderCrossDomainInfoLayout()
          : renderInfoLayout()}
      </div>
    </Drawer>
  );

  function onBackClick() {
    setIsShowCodeEditor(false);
  }
  async function onCopyClick() {
    const isOK = await copyToClipboard(formatJSONValue(data?.extra ?? ''));

    if (isOK) {
      Message.success('复制成功');
    } else {
      Message.error('复制失败');
    }
  }
}

export default EventDetailDrawer;
