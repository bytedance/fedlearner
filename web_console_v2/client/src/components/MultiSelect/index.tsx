/* istanbul ignore file */

import React, { FC } from 'react';

import { Select, Checkbox, Tag } from '@arco-design/web-react';
import { IconSearch } from '@arco-design/web-react/icon';

import { SelectProps } from '@arco-design/web-react/es/Select';
import styled from './index.module.less';
export interface OptionItem {
  /** Display label */
  label: string;
  /** Form value */
  value: any;
}

export interface Props extends SelectProps {
  value?: any[];
  onChange?: (val: any) => void;
  /**
   * DataSource
   */
  optionList: OptionItem[];
  /**
   * Hide header layout
   */
  isHideHeader?: boolean;
  /**
   * Hide index label
   */
  isHideIndex?: boolean;
}

const MultiSelect: FC<Props> = ({
  value,
  onChange = () => {},
  optionList,
  isHideHeader = false,
  isHideIndex = false,
  ...props
}) => {
  const isAllChecked = value?.length === optionList.length;
  return (
    <Select
      mode="multiple"
      value={value}
      arrowIcon={false}
      showSearch={true}
      suffixIcon={<IconSearch fontSize={14} />}
      onChange={(value, options) => {
        onChange(value);
      }}
      className={styled.select}
      dropdownRender={(menu) => (
        <div>
          {!isHideHeader && (
            <div className={styled.header}>
              <span className={styled.label_strong}>{`已选择 ${value?.length ?? 0} 项`}</span>
              <div>
                <span className={styled.label}>全选</span>
                <Checkbox
                  disabled={!optionList || optionList.length === 0}
                  checked={isAllChecked}
                  onChange={(checked: boolean) => {
                    if (checked) {
                      onChange(optionList.map((item) => item.value));
                    } else {
                      onChange([]);
                    }
                  }}
                />
              </div>
            </div>
          )}
          {menu}
        </div>
      )}
      renderTag={
        isAllChecked
          ? (props: any) => {
              // only show first item
              if (props.value !== optionList[0]?.value) {
                return null as any;
              }
              return (
                <Tag
                  closable
                  onClose={() => {
                    onChange([]);
                  }}
                >
                  全选
                </Tag>
              );
            }
          : undefined
      }
      {...props}
    >
      {optionList.map((item, index) => {
        return (
          <Select.Option key={item.value} value={item.value} title={item.label}>
            <div className={styled.item_cotainer}>
              <div>
                {!isHideIndex && <span className={styled.label_index}>{index + 1}</span>}
                <span className={styled.label_strong}>{item.label}</span>
              </div>
            </div>
          </Select.Option>
        );
      })}
    </Select>
  );
};

export default MultiSelect;
