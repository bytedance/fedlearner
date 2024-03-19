import React, { FC } from 'react';

import styles from './ProjectCardProp.module.less';

const ProjectCardProp: FC<{ label: string }> = ({ label, children }) => {
  return (
    <div className={styles.div_container}>
      <label className={styles.label_container}>{label}</label>
      <div className={styles.value_container}>{children}</div>
    </div>
  );
};

export default ProjectCardProp;
