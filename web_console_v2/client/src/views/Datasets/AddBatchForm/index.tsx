import React, {
  forwardRef,
  ForwardRefRenderFunction,
  ReactElement,
  useImperativeHandle,
} from 'react';
import styled from 'styled-components';
import { Form, message, Row, DatePicker, Checkbox } from 'antd';
import { useTranslation } from 'react-i18next';
import { DataBatchImportPayload, DatasetType } from 'typings/dataset';

import { useToggle } from 'react-use';
import { to } from 'shared/helpers';
import { startToImportDataBatch } from 'services/dataset';
import FileToImportList from './FileToImportList';
import { isEmpty } from 'lodash';
import dayjs from 'dayjs';

const Container = styled.div`
  .ant-form-item:not(.ant-form-item-with-help) {
    margin-bottom: 16px;
  }
`;
const FooterRow = styled(Row)`
  padding-top: 15px;
  border-top: 1px solid var(--backgroundColorGray);
`;

type Props = {
  datasetType?: DatasetType;
  datasetId?: ID;
  onSuccess?: any;
  onError?: (err: any) => void;
  renderButtons: (scope: { submitting: boolean }) => ReactElement;
};

export type AddBatchExposedRef = {
  validate: () => Promise<boolean>;
  submit: Function;
  toggleSubmit(v: boolean): void;
};

const AddBatchForm: ForwardRefRenderFunction<AddBatchExposedRef, Props> = (
  { datasetType, datasetId, renderButtons },
  parentRef,
) => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<DataBatchImportPayload>();
  const [submitting, toggleSubmit] = useToggle(false);

  useImperativeHandle(parentRef, () => {
    return { validate, submit, toggleSubmit };
  });

  return (
    <Container>
      <Form
        initialValues={{ move: false }}
        labelCol={{ span: 4 }}
        wrapperCol={{ span: 20 }}
        form={formInstance}
        style={{ width: '700px' }}
        labelAlign="left"
      >
        {datasetType === DatasetType.STREAMING && (
          <Form.Item
            name="event_time"
            label={t('dataset.label_event_time')}
            rules={[{ required: true, message: t('dataset.msg_event_time_required') }]}
          >
            <DatePicker
              format="YYYY-MM-DD HH:mm"
              showTime={{ format: 'HH:mm' }}
              placeholder={t('dataset.placeholder_event_time')}
            />
          </Form.Item>
        )}

        <Form.Item name="files" labelCol={{ span: 0 }} wrapperCol={{ span: 24 }}>
          <FileToImportList />
        </Form.Item>

        <Form.Item name="move" noStyle valuePropName="checked">
          <Checkbox style={{ position: 'absolute', bottom: '19px' }}>
            {t('dataset.label_move_file')}
          </Checkbox>
        </Form.Item>

        <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
          <FooterRow justify="end">{renderButtons({ submitting })}</FooterRow>
        </Form.Item>
      </Form>
    </Container>
  );

  function checkFilesSelection(): boolean {
    const files = formInstance.getFieldValue('files');
    return !isEmpty(files);
  }

  async function validate() {
    try {
      await formInstance.validateFields();
    } catch {
      return false;
    }

    const isFilesValid = checkFilesSelection();

    if (!isFilesValid) {
      // Please select file firstly
      message.warning(t('dataset.msg_file_required'));
      return false;
    }

    return true;
  }

  /**
   * @param datasetIdBackup prevent that datasetId from props is undefined
   * (most happens when invoke submit right after setDatasetId)
   */
  async function submit(datasetIdBackup?: ID) {
    const isValid = await validate();

    if (!isValid) throw new Error('FORM_VALIDATION_ERROR');

    const id = datasetId || datasetIdBackup;

    if (!id) {
      throw new Error(t('dataset.msg_id_required'));
    }

    toggleSubmit(true);

    const values = formInstance.getFieldsValue();

    values.event_time = dayjs(values.event_time).unix();

    const [res, error] = await to(startToImportDataBatch(id, values));

    if (error) {
      toggleSubmit(false);
      message.error(error.message);

      throw error;
    }

    toggleSubmit(false);

    return res;
  }
};

export default forwardRef(AddBatchForm);
