import React, { FC, useEffect, useMemo, useState } from 'react';

import { Table, Input, Grid, Tag, Space, Divider, Tooltip } from '@arco-design/web-react';
import { IconSearch } from '@arco-design/web-react/icon';
import { transformRegexSpecChar } from 'shared/helpers';
import GridRow from 'components/_base/GridRow';
import { Participant, ParticipantType } from 'typings/participant';
import { useRecoilQuery } from 'hooks/recoil';
import { participantListQuery } from 'stores/participant';
import ConnectionStatus from 'views/Partner/PartnerList/ConnectionStatus';
import { CONSTANTS } from 'shared/constants';
import { debounce } from 'lodash-es';

import styles from './index.module.less';

const { Row, Col } = Grid;

export const PartnerItem: FC<{
  data: Participant;
  isNeedTip?: boolean;
}> = ({ data, isNeedTip = false }) => {
  const isLightClient = data.type === ParticipantType.LIGHT_CLIENT;
  return (
    <div style={{ paddingRight: 2 }}>
      <GridRow gap={2} justify="space-between">
        <div className={styles.title_container}>
          <span className={styles.title_name}>{data.name}</span>
          <Tooltip content={data.comment}>
            <div className={`${styles.limited_length_text} choose `}>
              {data.comment || '无描述'}
            </div>
          </Tooltip>
        </div>

        <div className="choose">
          {data?.support_blockchain && (
            <Tag color="blue" size="small">
              区块链服务
            </Tag>
          )}
          {isLightClient ? (
            CONSTANTS.EMPTY_PLACEHOLDER
          ) : (
            <ConnectionStatus id={data.id} isNeedTip={isNeedTip} />
          )}
        </div>
      </GridRow>
    </div>
  );
};

interface Props {
  onChange?: (selectedParticipants: Participant[]) => void;
  participantsType: ParticipantType;
  isSupportCheckbox?: boolean;
}
const InvitionTable: FC<Props> = ({ onChange, participantsType, isSupportCheckbox = true }) => {
  const [filterText, setFilterText] = useState('');
  const [selectedParticipants, setSelectedParticipants] = useState<Participant[]>([]);
  // TODO: Need to filter out the successful connection
  const { isLoading, data: participantList } = useRecoilQuery(participantListQuery);

  const Title = (
    <Space split={<Divider type="vertical" />} size="medium">
      <span>
        {participantsType === ParticipantType.LIGHT_CLIENT ? '轻量级合作伙伴' : '标准合作伙伴'}
      </span>
      <Input
        prefix={<IconSearch />}
        placeholder="输入合作伙伴名称搜索"
        allowClear
        style={{ flexShrink: 0 }}
        onPressEnter={handleSearch}
        onChange={debounce((keyword) => {
          setFilterText(keyword);
        }, 300)}
      />
    </Space>
  );
  const columns = [
    {
      title: Title,
      render: (text: any, record: any) => <PartnerItem data={record} />,
    },
  ];

  const showList = useMemo(() => {
    if (participantList) {
      const regx = new RegExp(`^.*${transformRegexSpecChar(filterText)}.*$`);
      return participantList.filter((item) => {
        return (
          regx.test(item.name) &&
          (item.type === participantsType ||
            (!item.type && participantsType === ParticipantType.PLATFORM))
        );
      });
    }
    return [];
  }, [participantList, filterText, participantsType]);

  useEffect(() => {
    if (participantsType) {
      setSelectedParticipants([]);
    }
  }, [participantsType]);
  return (
    <>
      <Table
        className={styles.table_container}
        columns={columns}
        data={showList}
        rowKey="id"
        rowSelection={{
          selectedRowKeys: selectedParticipants.map((item) => item.id),
          checkCrossPage: true,
          onChange: onValueChange,
          type:
            isSupportCheckbox && participantsType === ParticipantType.PLATFORM
              ? 'checkbox'
              : 'radio',
          preserveSelectedRowKeys: true,
        }}
        pagination={{
          pageSize: 5,
          showTotal: true,
          total: showList.length,
          hideOnSinglePage: true,
        }}
        loading={isLoading}
      />
      <Row gutter={24} className={styles.select_container}>
        <Col span={4} className={styles.select_content_left}>
          已选{selectedParticipants.length}个
        </Col>
        <Col span={20} className={styles.select_content_right}>
          <Space wrap>
            {selectedParticipants.map((item) => (
              <Tag
                key={item.id}
                color="arcoblue"
                closable
                onClose={() => {
                  removeTag(item.id);
                }}
              >
                {item.name}
              </Tag>
            ))}
          </Space>
        </Col>
      </Row>
    </>
  );

  function handleSearch(e: any) {
    setFilterText(e.target.value);
    // Block the enter event of the submit button of the form
    e.preventDefault();
  }
  function onValueChange(selectedRowKeys: ID[], selectedRows: Participant[]) {
    onChange?.(selectedRows);
    setSelectedParticipants(selectedRows);
  }
  function removeTag(id: ID) {
    const newSelectParticipants = selectedParticipants.filter((item) => item.id !== id);
    setSelectedParticipants(newSelectParticipants);
    onChange?.(newSelectParticipants);
  }
};

export default InvitionTable;
