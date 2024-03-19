import React, { FC } from 'react';
import { Drawer } from '@arco-design/web-react';
import CodeEditor from 'components/CodeEditor';
type Props = {
  title: React.ReactNode;
  visible: boolean;
  onClose: () => void;
  code: string;
};
const SchedulerPipelineDrawer: FC<Props> = ({ title, visible, onClose, code }) => {
  return (
    <Drawer width={500} title={title} visible={visible} onOk={onClose} onCancel={onClose}>
      <CodeEditor value={code} language="json" theme="grey" />
    </Drawer>
  );
};

export default SchedulerPipelineDrawer;
