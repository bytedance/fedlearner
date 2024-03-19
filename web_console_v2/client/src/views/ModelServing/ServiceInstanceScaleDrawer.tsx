import React, { FC } from 'react';
import { Spin } from '@arco-design/web-react';
import { ModelServing } from 'typings/modelServing';
import InstanceNumberInput from './InstanceNumberInput';
import drawerConfirm from 'components/DrawerConfirm';

import styles from './ServiceInstanceScaleDrawer.module.less';

export type TProps = {
  service?: ModelServing;
  onChange?: (instanceNum: number) => void;
};

const ModelServingScaleDrawer: FC<TProps> = ({ service, onChange }) => {
  return (
    <div>
      {!service ? (
        <Spin loading={true} />
      ) : (
        <>
          <div className={styles.div_container}>
            <p className={styles.title_container}>实例规格</p>
            <p className={styles.text_container}>
              {service?.resource?.cpu} + {service?.resource?.memory}
            </p>
          </div>
          <div className={styles.div_container} style={{ marginTop: 20 }}>
            <p className={styles.title_container}>实例数</p>
            <InstanceNumberInput
              min={1}
              max={100}
              precision={0}
              defaultValue={service?.resource?.replicas}
              onChange={onChange}
            />
          </div>
        </>
      )}
    </div>
  );
};

export function handleScaleEdit(
  service: ModelServing,
  onUpdate: (instanceNum: number) => Promise<any>,
) {
  drawerConfirm({
    title: '扩缩容',
    okText: '确认',
    cancelText: '取消',
    onOk: (instanceNum: number) => {
      return onUpdate(instanceNum);
    },
    renderContent(setOkParams) {
      return <ModelServingScaleDrawer service={service} onChange={setOkParams} />;
    },
  });
}

export default ModelServingScaleDrawer;
