import React, { FC, useState } from 'react';
import { Button, Drawer, Space } from '@arco-design/web-react';
import ClickToCopy from 'components/ClickToCopy';
import { Copy } from 'components/IconPark';
import CodeEditor from 'components/CodeEditor';
import { formatJSONValue } from 'shared/helpers';
import { CONSTANTS } from 'shared/constants';

import { ModelServing } from 'typings/modelServing';

import styles from './index.module.less';

type Props = {
  data?: ModelServing;
  isShowLabel?: boolean;
  isShowSignature?: boolean;
};

const UserGuideTab: FC<Props> = ({ data, isShowLabel, isShowSignature = true }) => {
  const [drawerVisible, setDrawerVisible] = useState<boolean>(false);

  // TODO: user guide field
  const feature = CONSTANTS.EMPTY_PLACEHOLDER;
  const url = data?.endpoint ?? CONSTANTS.EMPTY_PLACEHOLDER;

  return (
    <div className={styles.div_container}>
      <Space size="medium">
        <div className={styles.content_block}>
          <p className={styles.label_container}>访问地址</p>
          <div className={styles.info_item_container}>
            <ClickToCopy text={String(url)}>
              <Space size="medium">
                <span>{url}</span>
                <Copy className={styles.copy_icon_container} />
              </Space>
            </ClickToCopy>
          </div>
        </div>
        {isShowSignature && (
          <div className={styles.content_block}>
            <p className={styles.label_container}>Signature</p>
            <Button className={styles.open_signature_btn} onClick={toggleDrawerVisible}>
              查看
            </Button>
          </div>
        )}
        {isShowLabel && (
          <div className={styles.content_block}>
            <p className={styles.label_container}>本侧特征</p>
            <p className={styles.label_container}>{feature}</p>
          </div>
        )}
      </Space>
      <Drawer
        width={720}
        visible={drawerVisible}
        title={'Signature'}
        closable={true}
        onCancel={toggleDrawerVisible}
      >
        <CodeEditor
          language="json"
          isReadOnly={true}
          theme="grey"
          value={data?.signature ? formatJSONValue(data.signature) : ''}
        />
      </Drawer>
    </div>
  );

  function toggleDrawerVisible() {
    setDrawerVisible(!drawerVisible);
  }
};

export default UserGuideTab;
