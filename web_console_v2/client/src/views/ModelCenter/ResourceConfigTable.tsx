import React from 'react';
import { CONSTANTS } from 'shared/constants';
import { ModelJob } from 'typings/modelCenter';
import { Tag, Popover, PopoverProps, TableColumnProps, Table } from '@arco-design/web-react';

import styles from './ResourceConfigTable.module.less';

const columns: TableColumnProps[] = [
  {
    title: '',
    dataIndex: 'type',
    render(value: string) {
      return <Tag>{value.toUpperCase()}</Tag>;
    },
  },
  {
    title: '',
    dataIndex: 'cpu',
  },
  {
    title: '',
    dataIndex: 'mem',
  },
  {
    title: '',
    dataIndex: 'replicas',
  },
];

function genText(field: string, value: number) {
  if (/cpu$/i.test(field)) {
    return `${Math.floor(value / 1000)} Core`;
  }
  if (/mem$/i.test(field)) {
    return `${value} GiB`;
  }
  if (/replicas$/i.test(field)) {
    return `${value} 实例数`;
  }
}

type ResourceConfigTableProps = {
  job: ModelJob;
};

type ResourceConfigTableButtonProps = ResourceConfigTableProps & {
  btnText?: string;
  popoverProps?: PopoverProps;
};

const ResourceConfigTable: React.FC<ResourceConfigTableProps> & {
  Button: React.FC<ResourceConfigTableButtonProps>;
} = ({ job }) => {
  const { config } = job;

  if (!config) {
    return null;
  }

  const { job_definitions } = config;
  const { variables } = job_definitions[0];
  const group: any = {};

  for (const item of variables) {
    if (!/cpu|mem|replica/i.test(item.name)) {
      continue;
    }

    const [type, prop] = item.name.split('_');
    if (!group[type]) {
      group[type] = {};
    }

    const numericVal = parseInt(item.value);

    if (numericVal > 0) {
      group[type][prop] = genText(item.name, numericVal);
    }
  }
  const tableData = ['master', 'ps', 'worker']
    .filter((type) => group[type] != null)
    .map((type) => {
      return {
        type,
        cpu: CONSTANTS.EMPTY_PLACEHOLDER,
        mem: CONSTANTS.EMPTY_PLACEHOLDER,
        replicas: CONSTANTS.EMPTY_PLACEHOLDER,
        ...group[type],
      };
    });

  return (
    <Table
      rowKey="type"
      className={`${styles.table_container} custom-table`}
      border={false}
      showHeader={false}
      size="small"
      columns={columns}
      data={tableData}
      pagination={false}
    />
  );
};

const PopoverButton: React.FC<ResourceConfigTableButtonProps> = ({
  job,
  btnText = '查看',
  popoverProps = {},
}) => {
  return (
    <Popover
      {...popoverProps}
      content={<ResourceConfigTable job={job} />}
      getPopupContainer={() => document.body}
    >
      <button className="custom-text-button">{btnText}</button>
    </Popover>
  );
};

ResourceConfigTable.Button = PopoverButton;

export default ResourceConfigTable;
