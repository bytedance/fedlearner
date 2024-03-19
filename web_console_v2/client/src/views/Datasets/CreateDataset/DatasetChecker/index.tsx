import React, { useEffect, useMemo, useState } from 'react';
import { DATASET_SCHEMA_CHECKER } from 'typings/dataset';
import { Checkbox, Space } from '@arco-design/web-react';
import TitleWithIcon from 'components/TitleWithIcon';
import { IconInfoCircle } from '@arco-design/web-react/icon';

interface IDatasetChecker {
  value?: DATASET_SCHEMA_CHECKER[];
  onChange?: (val: DATASET_SCHEMA_CHECKER[]) => void;
}

export default function DatasetChecker(props: IDatasetChecker) {
  const { value, onChange } = props;
  const [checkState, setCheckState] = useState({
    join: true,
    numeric: false,
  });
  useEffect(() => {
    const newValue: DATASET_SCHEMA_CHECKER[] = [];
    !!checkState.join && newValue.push(DATASET_SCHEMA_CHECKER.RAW_ID_CHECKER);
    !!checkState.numeric && newValue.push(DATASET_SCHEMA_CHECKER.NUMERIC_COLUMNS_CHECKER);
    onChange?.(newValue);
  }, [checkState, onChange]);

  const updateState = (key: 'join' | 'numeric') => {
    setCheckState((pre) => ({
      ...pre,
      [key]: !pre[key],
    }));
  };

  const isJoinChecked = useMemo(() => {
    return Array.isArray(value) && value.includes(DATASET_SCHEMA_CHECKER.RAW_ID_CHECKER);
  }, [value]);
  const isNumericChecked = useMemo(() => {
    return Array.isArray(value) && value.includes(DATASET_SCHEMA_CHECKER.NUMERIC_COLUMNS_CHECKER);
  }, [value]);
  return (
    <Space size="large">
      <Checkbox
        checked={isJoinChecked}
        onChange={() => {
          updateState('join');
        }}
      >
        {
          <TitleWithIcon
            isShowIcon={true}
            isBlock={false}
            title="求交数据校验"
            icon={IconInfoCircle}
            tip="当数据集需用于求交时，需勾选该选项，将要求数据集必须有raw_id 列且没有重复值"
          />
        }
      </Checkbox>
      <Checkbox
        checked={isNumericChecked}
        onChange={() => {
          updateState('numeric');
        }}
      >
        {
          <TitleWithIcon
            isShowIcon={true}
            isBlock={false}
            title="全数值特征校验"
            icon={IconInfoCircle}
            tip="当数据集需用于树模型训练时，需勾选该选项，将要求数据集特征必须为全数值"
          />
        }
      </Checkbox>
    </Space>
  );
}
