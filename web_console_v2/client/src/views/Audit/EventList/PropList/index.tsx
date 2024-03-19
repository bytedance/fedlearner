import React, { FC, ReactNode } from 'react';

import { Grid } from '@arco-design/web-react';
import { Label, LabelStrong } from 'styles/elements';
import { Copy } from 'components/IconPark';
import ClickToCopy from 'components/ClickToCopy';

import styles from './index.module.less';

const { Row, Col } = Grid;
export interface Item {
  key: string;
  value: ReactNode;
  isCanCopy?: boolean;
  onClick?: () => void;
}
export interface Props {
  list: Item[];
}

const PropList: FC<Props> = ({ list }) => {
  return (
    <>
      {list.map((item) => {
        return (
          <Row className={styles.styled_row} key={item.key}>
            <Col span={4}>
              <Label>{item.key}</Label>
            </Col>
            <Col span={20}>
              {item.isCanCopy ? (
                <ClickToCopy text={String(item.value)}>
                  <LabelStrong onClick={item.onClick}>
                    {item.value}
                    <Copy className={styles.styled_copy_icon} />
                  </LabelStrong>
                </ClickToCopy>
              ) : (
                <LabelStrong onClick={item.onClick}>{item.value}</LabelStrong>
              )}
            </Col>
          </Row>
        );
      })}
    </>
  );
};

export default PropList;
