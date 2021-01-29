import React, { ReactElement } from 'react';
import { Drawer } from 'antd';
import { Project } from 'typings/project';
import DetailBody from './DetailBody';
import DetailHeader from './DetailHeader';
import { Close } from 'components/IconPark';
import IconButton from 'components/IconButton';

interface DetailProps {
  visible: boolean;
  onClose: () => void;
  project?: Project;
}

function CloseButton(): ReactElement {
  return <IconButton icon={<Close />} />;
}

function ProjectDetailDrawer({ visible, onClose, project }: DetailProps) {
  if (!project) return null;

  return (
    <Drawer
      placement="right"
      closable={true}
      width={880}
      zIndex={1999}
      closeIcon={<CloseButton />}
      visible={visible}
      onClose={onClose}
      title={<DetailHeader project={project} />}
    >
      <DetailBody project={project} />
    </Drawer>
  );
}

export default ProjectDetailDrawer;
