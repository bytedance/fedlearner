import React, { FC, useContext, memo } from 'react';
import { Form, Input } from '@arco-design/web-react';
import NoResult from 'components/NoResult';
import SlotEntryItem from './SlotEntryItem';
import styled from './index.module.less';
import { SlotEntries } from 'views/WorkflowTemplates/TemplateForm/stores';
import { useSearchBox } from '../hooks';
import { SearchBox } from '../elements';
import { ComposeDrawerContext } from '../index';

type Props = {
  slotList?: SlotEntries;
  isCheck?: boolean;
};

const SlotEntryList: FC<Props> = ({ isCheck }) => {
  const { filter, onFilterChange, onInputKeyPress } = useSearchBox();
  const context = useContext(ComposeDrawerContext);
  const slotList = context.formData?._slotEntries;

  return (
    <>
      <SearchBox>
        <Input.Search
          placeholder="按名字搜索插槽"
          onChange={onFilterChange}
          onKeyPress={onInputKeyPress}
        />
      </SearchBox>

      <Form.List field="_slotEntries">
        {(entries) => {
          const filtedItems = entries.filter(slotNameFilter);

          return (
            <div className={styled.slot_list_row}>
              {/* 2 column layout */}
              <div className={styled.slot_list_col}>
                {filtedItems
                  .filter((_, index) => index % 2 === 0)
                  .map((entry) => (
                    <Form.Item noStyle field={entry.field} key={'_slotEntries' + entry.key}>
                      <SlotEntryItem isCheck={isCheck} path={entry.field} />
                    </Form.Item>
                  ))}
              </div>

              <div className={styled.slot_list_col}>
                {filtedItems
                  .filter((_, index) => index % 2 === 1)
                  .map((entry) => (
                    <Form.Item
                      {...entry}
                      noStyle
                      field={entry.field}
                      key={'_slotEntries' + entry.key}
                    >
                      <SlotEntryItem isCheck={isCheck} path={entry.field} />
                    </Form.Item>
                  ))}
              </div>

              {entries.length === 0 && (
                <NoResult
                  noImage
                  text="该任务没有插槽"
                  style={{ margin: '50px auto 20px', width: '100%' }}
                />
              )}
            </div>
          );
        }}
      </Form.List>
    </>
  );

  function slotNameFilter(_: any, index: number) {
    if (!slotList) return true;

    const matcher = filter.toLowerCase();
    const [slotName, slot] = slotList[index] ?? [];

    return slotName?.toLowerCase().includes(matcher) || slot?.label.includes(matcher);
  }
};

export default memo(SlotEntryList);
