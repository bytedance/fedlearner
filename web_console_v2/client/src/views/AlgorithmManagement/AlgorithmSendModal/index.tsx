import React, { FC } from 'react';
import { Modal, Typography, Input, Message } from '@arco-design/web-react';
import { IconLoading } from '@arco-design/web-react/icon';
import PropertyList from 'components/PropertyList';
import { Algorithm, AlgorithmProject } from 'typings/algorithm';
import AlgorithmType from 'components/AlgorithmType';
import { ConfirmProps } from '@arco-design/web-react/es/Modal/confirm';
import styled from './index.module.less';

type Props = {
  algorithm: Algorithm | AlgorithmProject;
  isPublish?: boolean;
  onChange: (comment: string) => void;
};

const { Text } = Typography;
const { TextArea } = Input;

const AlgorithmSendModalContent: FC<Props> = ({ isPublish = false, algorithm, onChange }) => {
  const curVersion =
    (algorithm as AlgorithmProject).latest_version || (algorithm as Algorithm).version || 0;
  const propertyList = [
    {
      label: '名称',
      value: algorithm.name,
    },
    {
      label: '类型',
      value: algorithm?.type && <AlgorithmType type={algorithm.type} style={{ marginTop: -4 }} />,
    },
    {
      label: '版本',
      value: `V${isPublish ? curVersion + 1 : curVersion}`,
    },
    {
      label: '描述',
      value: algorithm.comment,
    },
  ];
  return (
    <div className={styled.styled_container}>
      <Text type="secondary">{'算法'}</Text>
      <PropertyList className={styled.styled_property_list} cols={2} properties={propertyList} />
      {isPublish ? (
        <>
          <Text type="secondary">{'版本描述'}</Text>
          <TextArea style={{ marginTop: 6 }} rows={2} onChange={onChange} />
        </>
      ) : (
        <></>
      )}
    </div>
  );
};

function sendModal(
  algorithmGetter: Props['algorithm'] | (() => Promise<Props['algorithm']>),
  onConfirm: (comment: string, algorithm: Props['algorithm']) => Promise<any>,
  onCancel: () => void,
  isPublish = false,
  showMsg = false,
) {
  return new Promise(async (resolve) => {
    let algorithm: Props['algorithm'] | undefined = undefined;
    const modalProps: ConfirmProps = {
      icon: null,
      title: <IconLoading />,
      closable: true,
      style: {
        width: '600px',
      },
      okButtonProps: {
        disabled: true,
      },
      okText: isPublish ? '发版' : '发布',
      content: null,
      cancelText: '取消',
      onCancel,

      async onConfirm() {
        if (!algorithm) {
          return;
        }
        modalProps.confirmLoading = true;
        modal.update({ ...modalProps });
        try {
          await onConfirm(curComment, algorithm);
        } catch (e) {
          Message.error(e.message);
          throw e;
        }
        if (showMsg) {
          Message.success(isPublish ? '发版成功' : '发布成功');
        }

        modal.close();
        resolve('');
      },
    };
    const algorithmPromise =
      typeof algorithmGetter === 'function' ? algorithmGetter() : Promise.resolve(algorithmGetter);

    const modal = Modal.confirm({ ...modalProps });

    algorithm = await algorithmPromise;
    let curComment = algorithm.comment ?? '';

    // update the modal content and state with algorithm data
    modalProps.title = isPublish ? `发版「${algorithm.name}」` : `发布${algorithm.name}」`;
    modalProps.content = (
      <AlgorithmSendModalContent
        isPublish={isPublish}
        algorithm={algorithm}
        onChange={(value: string) => {
          curComment = value;
        }}
      />
    );
    modalProps.okButtonProps = {
      disabled: false,
    };
    modal.update({ ...modalProps });
  });
}

export default sendModal;
