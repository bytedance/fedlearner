import React, { useMemo } from 'react';
import { Alert, Button, Drawer, Table, Tag } from '@arco-design/web-react';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import { TABLE_COL_WIDTH } from 'shared/constants';
import ClickToCopy from 'components/ClickToCopy';
import { useToggle } from 'react-use';
import { DataJoinType } from 'typings/dataset';
import './index.less';

type Props = {
  joinType: DataJoinType;
};

type LevelInfo = {
  name: string;
  desc: string;
};
type ParamsInfo = {
  sender: {
    cpu: string;
    mem: string;
  };
  receiver: {
    cpu: string;
    mem: string;
  };
};

type ParamsTableData = {
  id: number;
  level: LevelInfo;
  replicas?: string | number;
  num_partition?: number | string;
  part_num?: number | string;
  master?: ParamsInfo | string | number;
  raw_data_worker?: ParamsInfo;
  psi_join_worker?: ParamsInfo;
  totalCost: ParamsInfo | string[];
};

/**
 * TODO: Temporary table component, which will be removed later
 */
const recommendedParams: ParamsTableData[] = [
  {
    id: 1,
    level: {
      name: '微型数据集',
      desc: '(数据量 ≤ 1万且数据大小 ≤ 1g)',
    },
    num_partition: 1,
    master: {
      sender: { cpu: '2000m', mem: '4Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    raw_data_worker: {
      sender: { cpu: '4000m', mem: '8Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    psi_join_worker: {
      sender: { cpu: '4000m', mem: '8Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    totalCost: {
      sender: { cpu: '6000m', mem: '12Gi' },
      receiver: { cpu: '3000m', mem: '6Gi' },
    },
  },
  {
    id: 2,
    level: {
      name: '小型数据集',
      desc: '(1万 < 数据集样本量 ≤ 100万或1g ≤ 数据大小 ≤ 10g)',
    },
    num_partition: 4,
    master: {
      sender: { cpu: '2000m', mem: '4Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    raw_data_worker: {
      sender: { cpu: '4000m', mem: '8Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    psi_join_worker: {
      sender: { cpu: '4000m', mem: '8Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    totalCost: {
      sender: { cpu: '18000m', mem: '36Gi' },
      receiver: { cpu: '6000m', mem: '12Gi' },
    },
  },
  {
    id: 3,
    level: {
      name: '中型数据集',
      desc: '(100万 < 数据集样本量 ≤ 1亿或10g < 数据大小 ≤ 100g)',
    },
    num_partition: 16,
    master: {
      sender: { cpu: '2000m', mem: '4Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    raw_data_worker: {
      sender: { cpu: '8000m', mem: '16Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    psi_join_worker: {
      sender: { cpu: '8000m', mem: '16Gi' },
      receiver: { cpu: '1000m', mem: '2Gi' },
    },
    totalCost: {
      sender: { cpu: '130000m', mem: '260Gi' },
      receiver: { cpu: '18000m', mem: '36Gi' },
    },
  },
  {
    id: 4,
    level: {
      name: '大型数据集',
      desc: '(数据集样本量 > 1亿或数据大小 > 100g)',
    },
    num_partition: 32,
    master: {
      sender: { cpu: '2000m', mem: '4Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    raw_data_worker: {
      sender: { cpu: '16000m', mem: '32Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    psi_join_worker: {
      sender: { cpu: '16000m', mem: '32Gi' },
      receiver: { cpu: '2000m', mem: '4Gi' },
    },
    totalCost: {
      sender: { cpu: '514000m', mem: '1028Gi' },
      receiver: { cpu: '66000m', mem: '132Gi' },
    },
  },
];

const recommendedOTPSIParams: ParamsTableData[] = [
  {
    id: 1,
    level: {
      name: '小型数据集',
      desc: '(0万 < 数据集样本量 ≤ 400万)',
    },
    num_partition: 1,
    replicas: 1,
    totalCost: ['spark任务动态分配资源', 'OtPsi：2c4g'],
  },
  {
    id: 2,
    level: {
      name: '中型数据集',
      desc: '(数据集样本量 > 400w)',
    },
    num_partition: 'max(发起方样本量,合作方样本量)/400万',
    replicas: '5或10',
    totalCost: ['spark任务动态分配资源', 'OtPsi：10c20g或20c40g'],
  },
];

const recommendedHASHParams: ParamsTableData[] = [
  {
    id: 1,
    level: {
      name: '小型数据集',
      desc: '(0万 < 数据集样本量 ≤ 400万)',
    },
    num_partition: 1,
    replicas: 1,
    totalCost: ['spark任务动态分配资源', 'OtPsi：2c4g'],
  },
  {
    id: 2,
    level: {
      name: '中型数据集',
      desc: '(数据集样本量 > 400w)',
    },
    num_partition: 'max(发起方样本量,合作方样本量)/400万',
    replicas: '5或10',
    totalCost: ['spark任务动态分配资源', 'OtPsi：10c20g或20c40g'],
  },
];

const recommendedLightRSAPSIParams: ParamsTableData[] = [
  {
    id: 1,
    level: {
      name: '小型数据集',
      desc: '(0万 < 数据集样本量 ≤ 200万)',
    },
    part_num: 1,
    totalCost: ['spark任务动态分配资源', 'rsa求交：16c20g'],
  },
  {
    id: 2,
    level: {
      name: '中型数据集',
      desc: '(数据集样本量 > 200w)',
    },
    part_num: 'max(发起方样本量,合作方样本量)/200万',
    totalCost: ['spark任务动态分配资源', 'rsa求交：16c20g'],
  },
];

const RECOMMENDED_PARAMS = {
  [DataJoinType.PSI]: recommendedParams,
  [DataJoinType.OT_PSI_DATA_JOIN]: recommendedOTPSIParams,
  [DataJoinType.HASH_DATA_JOIN]: recommendedHASHParams,
  [DataJoinType.NORMAL]: [],
  [DataJoinType.LIGHT_CLIENT]: recommendedLightRSAPSIParams,
  [DataJoinType.LIGHT_CLIENT_OT_PSI_DATA_JOIN]: [],
};

const TIPS_MAPPER = {
  [DataJoinType.PSI]:
    '请根据各方可用资源情况，选择数据集配置。当样本量和数据大小命中不同的规则时，请选择更大的资源规格。',
  [DataJoinType.OT_PSI_DATA_JOIN]: '请根据各方可用资源情况，选择数据集配置。',
  [DataJoinType.HASH_DATA_JOIN]: '请根据各方可用资源情况，选择数据集配置。',
  [DataJoinType.NORMAL]: '',
  [DataJoinType.LIGHT_CLIENT]: '请根据各方可用资源情况，选择数据集配置。',
  [DataJoinType.LIGHT_CLIENT_OT_PSI_DATA_JOIN]: '',
};

const Title: React.FC<Props> = ({ joinType }) => {
  const [drawerVisible, setDrawerVisible] = useToggle(false);
  const columns: ColumnProps<any>[] = useMemo(() => {
    switch (joinType) {
      case DataJoinType.PSI:
        return [
          {
            title: '所有参与方最大数据量级',
            dataIndex: 'level',
            fixed: 'left',
            width: TABLE_COL_WIDTH.NORMAL,
            render: (_) => {
              return renderLevel(_);
            },
          },
          {
            title: 'num_partition',
            dataIndex: 'num_partition',
            width: TABLE_COL_WIDTH.THIN,
          },
          {
            title: 'master',
            dataIndex: 'master',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderParams(_);
            },
          },
          {
            title: 'raw_worker',
            dataIndex: 'raw_data_worker',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderParams(_);
            },
          },
          {
            title: 'psi_worker',
            dataIndex: 'psi_join_worker',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderParams(_);
            },
          },
          {
            title: '总资源消耗',
            dataIndex: 'totalCost',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderParams(_);
            },
          },
        ];
      case DataJoinType.OT_PSI_DATA_JOIN:
        return [
          {
            title: '所有参与方最大数据量级',
            dataIndex: 'level',
            fixed: 'left',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderLevel(_);
            },
          },
          {
            title: 'num_partition',
            dataIndex: 'num_partition',
            width: TABLE_COL_WIDTH.THIN,
          },
          {
            title: 'replicas',
            dataIndex: 'replicas',
            width: TABLE_COL_WIDTH.THIN / 2,
          },
          {
            title: '总资源消耗',
            dataIndex: 'totalCost',
            width: TABLE_COL_WIDTH.THIN,
            render: (_: string[]) => {
              return (
                <ul>
                  {_.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              );
            },
          },
        ];
      case DataJoinType.LIGHT_CLIENT:
        return [
          {
            title: '所有参与方最大数据量级',
            dataIndex: 'level',
            fixed: 'left',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderLevel(_);
            },
          },
          {
            title: 'part_num',
            dataIndex: 'part_num',
            width: TABLE_COL_WIDTH.THIN,
          },
          {
            title: '总资源消耗',
            dataIndex: 'totalCost',
            width: TABLE_COL_WIDTH.THIN,
            render: (_: string[]) => {
              return (
                <ul>
                  {_.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              );
            },
          },
        ];
      case DataJoinType.HASH_DATA_JOIN:
        return [
          {
            title: '所有参与方最大数据量级',
            dataIndex: 'level',
            fixed: 'left',
            width: TABLE_COL_WIDTH.THIN,
            render: (_) => {
              return renderLevel(_);
            },
          },
          {
            title: 'num_partition',
            dataIndex: 'num_partition',
            width: TABLE_COL_WIDTH.THIN,
          },
          {
            title: 'replicas',
            dataIndex: 'replicas',
            width: TABLE_COL_WIDTH.THIN / 2,
          },
          {
            title: '总资源消耗',
            dataIndex: 'totalCost',
            width: TABLE_COL_WIDTH.THIN,
            render: (_: string[]) => {
              return (
                <ul>
                  {_.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              );
            },
          },
        ];
      default:
        return [];
    }
  }, [joinType]);
  const dataSource = useMemo(() => {
    if (!joinType) {
      return [];
    }
    return RECOMMENDED_PARAMS[joinType] || [];
  }, [joinType]);
  return (
    <div className="recommended-param-table">
      <Drawer
        title={<span className="main-title">推荐配置</span>}
        className="recommend-param-drawer"
        style={{
          width: 800,
        }}
        visible={drawerVisible}
        onCancel={() => setDrawerVisible(false)}
      >
        <Alert className={'params-tips'} content={TIPS_MAPPER[joinType]} />
        <Table
          pagination={false}
          scroll={{ x: 1000, y: 600 }}
          border={{ wrapper: true, cell: true }}
          className="custom-table custom-table-left-side-filter"
          rowKey={'id'}
          columns={columns}
          data={dataSource}
        />
      </Drawer>
      <Button
        onClick={() => {
          setDrawerVisible(true);
        }}
        size={'mini'}
        type="text"
      >
        推荐配置参数
      </Button>
    </div>
  );

  function renderLevel(levelInfo: LevelInfo) {
    return (
      <div>
        <h5>{levelInfo.name}</h5>
        <span>{levelInfo.desc}</span>
      </div>
    );
  }

  function renderParams(paramInfo: ParamsInfo) {
    return (
      <div>
        <h5>发起方:</h5>
        <span>
          <ClickToCopy text={paramInfo?.sender?.cpu}>
            <Tag className="params-title-tag" color={'arcoblue'}>
              {'CPU:'}
            </Tag>
            {paramInfo?.sender?.cpu}
          </ClickToCopy>
          <ClickToCopy text={paramInfo?.sender?.mem}>
            <Tag className="params-title-tag" color={'green'}>
              {'MEM:'}
            </Tag>
            {paramInfo?.sender?.mem}
          </ClickToCopy>
        </span>
        <h5>合作伙伴:</h5>
        <span>
          <ClickToCopy text={paramInfo?.receiver?.cpu}>
            <Tag className="params-title-tag" color={'arcoblue'}>
              {'CPU:'}
            </Tag>
            {paramInfo?.receiver?.cpu}
          </ClickToCopy>
          <ClickToCopy text={paramInfo?.receiver?.mem}>
            <Tag className="params-title-tag" color={'green'}>
              {'MEM:'}
            </Tag>
            {paramInfo?.receiver?.mem}
          </ClickToCopy>
        </span>
      </div>
    );
  }
};

export default Title;
