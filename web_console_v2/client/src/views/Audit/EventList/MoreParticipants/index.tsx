import React, { FC } from 'react';
import { Popover, Tag } from '@arco-design/web-react';
import { PopoverProps } from '@arco-design/web-react/es/Popover';
import { TagProps } from '@arco-design/web-react/es/Tag';

import styles from './index.module.less';

export interface MoreParticipantsProps {
  textList: string[];
  count: number;
  popoverProps?: PopoverProps;
  tagProps?: TagProps;
}

const MoreParticipants: FC<MoreParticipantsProps> = (props: MoreParticipantsProps) => {
  const { textList = [], count = 1, popoverProps = {}, tagProps = {} } = props;
  function renderText(textList: string[], count: number) {
    const listLength = textList.length;
    if (listLength === 0) {
      return <div>-</div>;
    } else if (listLength <= count) {
      return <div>{textList.slice(0, count).join(' ')}</div>;
    }
    return (
      <>
        <span>{textList.slice(0, count)}</span>
        <Popover
          {...popoverProps}
          content={textList.map((item) => (
            <div>{item}</div>
          ))}
        >
          <Tag className={styles.tag_content} {...tagProps}>
            +{listLength - count}
          </Tag>
        </Popover>
      </>
    );
  }

  return renderText(textList, count);
};

export default MoreParticipants;
