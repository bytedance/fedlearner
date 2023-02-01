import React, { FC, useEffect, useState } from 'react';
import { Grid, Input, Radio, Typography, Button } from '@arco-design/web-react';
import { IconPlus, IconDelete } from '@arco-design/web-react/icon';
import styled from './index.module.less';
import { giveWeakRandomKey } from 'shared/helpers';
import { AlgorithmParams } from 'typings/modelCenter';

type TProps = {
  value?: AlgorithmParams[];
  defaultValue?: AlgorithmParams[];
  onChange?: (value: AlgorithmParams[]) => void;
};

const { Row, Col } = Grid;
const { Text } = Typography;
const { TextArea } = Input;

const emptyRow: AlgorithmParams = {
  name: '',
  value: '',
  display_name: '',
  comment: '',
  required: true,
};

type AlgorithmParamsState = {
  id: string;
  value: AlgorithmParams;
};

const AlgorithmParamsInput: FC<TProps> = ({ value, defaultValue, onChange }: TProps) => {
  const [curValue, setCurValue] = useState<Array<AlgorithmParamsState>>(
    getValue(value || defaultValue || []),
  );
  // 用 value 是否有值判断是否受控
  const isControlled = Array.isArray(value);

  useEffect(() => {
    if (isControlled) {
      setCurValue(getValue(value || []));
    }
  }, [value, isControlled]);

  return (
    <div className={styled.styled_container}>
      <>
        <Row gutter={10} className={styled.styled_row_with_border}>
          <Col span={7}>
            <Text className={styled.styled_required_text} type="secondary">
              {'名称'}
            </Text>
          </Col>
          <Col span={7}>
            <Text type="secondary">{'默认值'}</Text>
          </Col>
          <Col span={3}>
            <Text type="secondary">{'是否必填'}</Text>
          </Col>
          <Col span={7}>
            <Text type="secondary">{'提示语'}</Text>
          </Col>
        </Row>
        {curValue.map(({ id, value: item }, index) => (
          <Row className={styled.styled_row_without_border} gutter={10} key={id}>
            <Col span={7}>
              <Input
                placeholder={'请输入参数名称'}
                defaultValue={item.name}
                type="text"
                onBlur={getFormHandler(index, 'name')}
              />
            </Col>
            <Col span={7}>
              <TextArea
                rows={1}
                placeholder={'请输入默认值'}
                defaultValue={item.value}
                onBlur={getFormHandler(index, 'value')}
              />
            </Col>
            <Col span={3}>
              <Radio.Group
                className={styled.styled_radio_group}
                defaultValue={item.required}
                type="button"
                onChange={getFormHandler(index, 'required')}
              >
                <Radio value={true}>是</Radio>
                <Radio value={false}>否</Radio>
              </Radio.Group>
            </Col>
            <Col span={7}>
              <TextArea
                rows={1}
                placeholder={'请输入提示语'}
                defaultValue={item.comment}
                onBlur={getFormHandler(index, 'comment')}
              />
            </Col>
            <Button
              className={styled.styled_delete_button}
              onClick={(e: Event) => {
                e.preventDefault();
                e.stopPropagation();
                delRow(index);
              }}
              type="text"
              size="small"
              icon={<IconDelete />}
            />
          </Row>
        ))}
      </>
      <Button className={styled.styled_button} onClick={addRow} type="text" size="small">
        <IconPlus />
        {'新增超参数'}
      </Button>
    </div>
  );

  function setValue(value: AlgorithmParamsState[]) {
    // 如果受控，内部不处理 value，直接提交给外部处理，通过上方的 useEffect 来更新 curValue
    if (isControlled) {
      onChange?.(value.map((item) => item.value));
      return;
    }
    setCurValue(value);
  }

  function getFormHandler(index: number, field: keyof AlgorithmParams) {
    return (val: any | string) => {
      const newValue = [...curValue];
      const { id, value } = newValue[index];
      newValue[index] = {
        id,
        value: {
          ...value,
          [field]: typeof val === 'object' ? val?.target?.value : val,
        },
      };
      setValue([...newValue]);
    };
  }

  function addRow(e: any) {
    e.stopPropagation();
    e.preventDefault();
    const newValue = [...curValue, { id: `${Date.now()}`, value: { ...emptyRow } }];
    setValue(newValue);
  }
  function delRow(index: number) {
    setValue(curValue.filter((_, i) => i !== index));
  }
};

function getValue(value: AlgorithmParams[]) {
  return value.map((item) => ({
    id: item.name || giveWeakRandomKey(),
    value: item,
  }));
}

export default AlgorithmParamsInput;
