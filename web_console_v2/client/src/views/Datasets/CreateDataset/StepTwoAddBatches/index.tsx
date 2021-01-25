import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, message, Tooltip, Button, Switch, DatePicker, Popconfirm } from 'antd';
import { useTranslation } from 'react-i18next';
import { DataBatchImportPayload } from 'typings/dataset';
import GridRow from 'components/_base/GridRow';
import { useToggle } from 'react-use';
import { to } from 'shared/helpers';
import { createDataset, deleteDataset, startToImportDataBatch } from 'services/dataset';
import { QuestionCircle } from 'components/IconPark';
import FileList from './FileList';
import { useRecoilValue } from 'recoil';
import { datasetBasicForm } from 'stores/dataset';
import { isEmpty } from 'lodash';

const Container = styled.div`
  .ant-form-item:not(.ant-form-item-with-help) {
    margin-bottom: 16px;
  }
`;
const FooterRow = styled(GridRow)`
  padding-top: 15px;
  border-top: 1px solid var(--backgroundGray);
`;

type Props = {
  onCancel: any;
  onSuccess: any;
  onPrevious: any;
};

const StepTwoAddBatches: FC<Props> = ({ onSuccess, onPrevious, onCancel }) => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<DataBatchImportPayload>();
  const [submitting, toggleSubmit] = useToggle(false);

  const basicForm = useRecoilValue(datasetBasicForm);

  return (
    <Container>
      <Form
        initialValues={{ move: true }}
        labelCol={{ span: 4 }}
        wrapperCol={{ span: 20 }}
        form={formInstance}
        style={{ width: '700px' }}
        onFinish={submit}
        labelAlign="left"
      >
        <Form.Item
          name="event_time"
          label={t('dataset.label_event_time')}
          rules={[{ required: true, message: t('dataset.msg_event_time_required') }]}
        >
          <DatePicker
            format="YYYY-MM-DD HH:mm"
            showTime={{ format: 'HH:mm' }}
            placeholder={t('dataset.placeholder_name')}
          />
        </Form.Item>

        <Form.Item
          name="move"
          label={
            <Tooltip title={t('dataset.tip_move_file')}>
              <span style={{ margin: '0 5px 0 11px' }}>{t('dataset.label_move_file')}</span>
              <QuestionCircle />
            </Tooltip>
          }
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item labelCol={{ span: 0 }} wrapperCol={{ span: 24 }} name="files">
          <FileList />
        </Form.Item>

        <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
          <FooterRow justify="end" gap="12">
            <Popconfirm
              title={t('dataset.msg_quit_warning')}
              cancelText={t('cancel')}
              okText={t('submit')}
              onConfirm={onCancel}
            >
              <Button disabled={submitting}>{t('cancel')}</Button>
            </Popconfirm>

            <Button disabled={submitting} onClick={onPrevious}>
              {t('previous_step')}
            </Button>

            <Button type="primary" htmlType="submit" loading={submitting}>
              {t('dataset.btn_finish_n_import')}
            </Button>
          </FooterRow>
        </Form.Item>
      </Form>
    </Container>
  );

  function checkFilesSelection(): boolean {
    const files = formInstance.getFieldValue('files');
    return !isEmpty(files);
  }

  async function submit(values: DataBatchImportPayload) {
    const valid = checkFilesSelection();

    if (!valid) {
      // Select file firstly
      return message.warning(t('dataset.msg_file_required'));
    }

    toggleSubmit(true);

    const [createRes, createErr] = await to(createDataset({ ...basicForm }));
    const datasetId = createRes.data.id;

    if (createErr) {
      toggleSubmit(false);
      return message.error(createErr.message);
    }

    const [__, importErr] = await to(startToImportDataBatch({ ...values, dataset_id: datasetId }));

    if (importErr) {
      // If create dateset successfully but import error here
      // do delete dataset at once
      deleteDataset(datasetId).catch((error) => {
        // TODO: what if delete request failed as well?
        message.error(error.message);
      });

      toggleSubmit(false);
      return message.error(importErr.message);
    }

    message.success(t('dataset.msg_start_importing'));
    toggleSubmit(false);
    onSuccess();
  }
};

export default StepTwoAddBatches;
