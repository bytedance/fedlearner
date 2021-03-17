import React, { FC } from 'react';
import { Modal, Table, Button, Tooltip } from 'antd';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import IconButton from 'components/IconButton';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import { DataBatch } from 'typings/dataset';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { DataBatchImportProgress } from './ImportProgress';

type Props = {
  visible: boolean;
  records: DataBatch[];
  toggleVisible: (v: boolean) => void;
} & React.ComponentProps<typeof Modal>;

const BatchImportRecords: FC<Props> = ({ visible, toggleVisible, records, ...props }) => {
  const { t } = useTranslation();

  const columns = [
    {
      title: i18n.t('dataset.label_event_time'),
      dataIndex: 'event_time',
      key: 'event_time',
      ellipsis: true,
      render: (time: number) => {
        return <div>{formatTimestamp(time)}</div>;
      },
    },
    {
      title: i18n.t('dataset.status'),
      dataIndex: 'state',
      name: 'state',
      render: (_: any, record: DataBatch) => {
        return <DataBatchImportProgress batch={record} />;
      },
    },
    {
      title: i18n.t('dataset.col_files_size'),
      dataIndex: 'file_size',
      name: 'file_size',
      render: (fileSize: number) => {
        return <span>{fileSize.toLocaleString('en')} KB</span>;
      },
    },
    {
      title: i18n.t('created_at'),
      dataIndex: 'created_at',
      name: 'created_at',
      width: 190,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
    {
      title: i18n.t('operation'),
      dataIndex: 'operation',
      name: 'operation',
      render: (_: number, record: DataBatch) => (
        <Tooltip title="Coming soon">
          <Button
            size="small"
            disabled
            type="link"
            style={{ marginLeft: '-15px' }}
            onClick={onDeleteClick}
          >
            {t('delete')}
          </Button>
        </Tooltip>
      ),
    },
  ];

  return (
    <Modal
      title={t('dataset.title_create')}
      visible={visible}
      width={860}
      style={{ top: '20%' }}
      closeIcon={<IconButton icon={<Close />} onClick={closeModal} />}
      zIndex={Z_INDEX_GREATER_THAN_HEADER}
      onCancel={closeModal}
      okText={t('dataset.btn_add_batch')}
      {...props}
    >
      <Table size="small" dataSource={records} columns={columns} />
    </Modal>
  );

  function closeModal() {
    toggleVisible(false);
  }
  function onDeleteClick() {
    // TODO: coming soon
  }
};

export default BatchImportRecords;
