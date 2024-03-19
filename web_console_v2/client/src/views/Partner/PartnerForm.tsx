import React, { FC } from 'react';
import { Spin } from '@arco-design/web-react';
import { CreateParticipantPayload, UpdateParticipantPayload } from 'typings/participant';
import GridRow from 'components/_base/GridRow';
import AddPartnerForm from './AddPartnerForm';

interface Props {
  isEdit: boolean;
  data?: any;
  onSubmit: (payload: any) => Promise<void>;
}

const PartnerForm: FC<Props> = ({ isEdit, data, onSubmit }) => {
  const dataProps = isEdit && data ? { data } : {};

  return (
    <GridRow justify="center" style={{ minHeight: '100%' }} align="start">
      <Spin loading={isEdit && !data}>
        <div style={{ width: 600 }}>
          {(!isEdit || data) && (
            <AddPartnerForm onFinish={onFinish} {...dataProps} isEdit={isEdit} needAdd={false} />
          )}
        </div>
      </Spin>
    </GridRow>
  );
  function onFinish(value: any) {
    const valueOnly = value[0];
    let payload = {} as UpdateParticipantPayload | CreateParticipantPayload;
    if (!isEdit) {
      if (valueOnly?.extra?.is_manual_configured) {
        Object.keys(valueOnly).forEach((key: any) => {
          const _key = key as keyof CreateParticipantPayload;
          if (key === 'extra') {
            payload = {
              ...payload,
              is_manual_configured: valueOnly?.extra?.is_manual_configured ?? true,
              grpc_ssl_server_host: valueOnly?.extra?.grpc_ssl_server_host ?? 'x-host',
            };
          } else {
            payload = {
              ...payload,
              [key]: valueOnly[_key],
            };
          }
        });
      } else {
        payload = {
          name: valueOnly.name,
          domain_name: valueOnly.domain_name,
          is_manual_configured: valueOnly?.extra?.is_manual_configured ?? false,
          comment: valueOnly.comment,
          type: valueOnly.type,
        };
      }
    } else {
      data &&
        Object.keys(valueOnly).forEach((key: any) => {
          const _key = key as keyof UpdateParticipantPayload;
          if (key === 'extra') {
            if (valueOnly?.extra?.is_manual_configured) {
              const grpc_ssl_server_host = valueOnly?.extra?.grpc_ssl_server_host;
              if (grpc_ssl_server_host !== data?.extra?.grpc_ssl_server_host) {
                payload = {
                  ...payload,
                  grpc_ssl_server_host: valueOnly?.extra?.grpc_ssl_server_host,
                };
              }
            }
          } else {
            if (valueOnly[_key] !== data[_key]) {
              payload = {
                ...payload,
                [key]: valueOnly[_key],
              };
            }
          }
        });
    }
    payload && onSubmit(payload);
  }
};

export default PartnerForm;
