import React, { FC } from 'react';
import { Input, Grid, Button } from '@arco-design/web-react';
import { ModelServing } from 'typings/modelServing';
import Modal from 'components/Modal';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';

import styles from './ServiceEditModal.module.less';

export interface Props {
  service: ModelServing;
  onChange: (params: Partial<ModelServing>) => void;
}

const { Row, Col } = Grid;
const { TextArea } = Input;

const ServiceEditModal: FC<Props> = ({ service, onChange }) => {
  return (
    <div>
      <Row className={styles.row_container} gutter={16}>
        <Col className={styles.label_col_container} span={6}>
          <span className={styles.key_container}>在线服务名称</span>
        </Col>
        <Col span={18}>
          <span className={styles.value_container}>{service.name}</span>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col className={styles.label_col_container} span={6}>
          <span className={styles.key_container}>在线服务描述</span>
        </Col>
        <Col span={18}>
          <TextArea
            className={styles.text_area_container}
            placeholder={'请输入'}
            defaultValue={service.comment}
            rows={3}
            onChange={handleChange}
          />
        </Col>
      </Row>
    </div>
  );

  function handleChange(comment: string) {
    onChange({
      comment,
    });
  }
};

export default ServiceEditModal;
export function editService(service: ModelServing, onOk: (params: Partial<ModelServing>) => void) {
  let serviceParams: Partial<ModelServing> = {};
  serviceParams = { resource: service.resource, comment: service.comment };
  const modal = Modal.confirm({
    icon: null,
    title: '在线服务信息',
    content: (
      <ServiceEditModal
        service={service}
        onChange={(params) => {
          serviceParams = { ...serviceParams, ...params };
        }}
      />
    ),
    footer: [
      <ButtonWithPopconfirm
        key="back"
        buttonText={'取消'}
        onConfirm={() => {
          modal.close();
        }}
      />,
      <Button
        style={{ marginLeft: 12 }}
        key="submit"
        type="primary"
        onClick={async () => {
          await onOk(serviceParams);
          modal.close();
        }}
      >
        提交
      </Button>,
    ],
  });
}
