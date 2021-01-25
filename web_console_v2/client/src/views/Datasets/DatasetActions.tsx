import React, { FC } from 'react';
import styled from 'styled-components';
import { Dataset } from 'typings/dataset';
import GridRow from 'components/_base/GridRow';
import { useTranslation } from 'react-i18next';
import { Button } from 'antd';
import { isImportFailed } from 'shared/dataset';
import { ButtonType } from 'antd/lib/button';

const Container = styled(GridRow)`
  margin-left: ${(props: any) => (props.type === 'link' ? '-15px !important' : 0)};
`;

type Action = 'add-batch' | 'view-records' | 'delete';
type Props = {
  dataset: Dataset;
  type: ButtonType;
  onSuccess: (args: { action: Action; response: any }) => void;
};

const actions: Action[] = ['add-batch', 'view-records', 'delete'];

const DatasetActions: FC<Props> = ({ dataset, type = 'default', onSuccess }) => {
  const { t } = useTranslation();

  const clickHandler: Record<Action, any> = {
    'add-batch': onAddBatchClick,
    'view-records': onAddRecordClick,
    delete: onDeleteClick,
  };
  const disabled: Record<Action, boolean> = {
    'add-batch': isImportFailed(dataset),
    'view-records': false,
    delete: false,
  };
  const text = {
    'add-batch': t('dataset.btn_add_batch'),
    'view-records': t('dataset.btn_view_records'),
    delete: t('dataset.btn_delete'),
  };

  return (
    <Container {...{ type }}>
      {actions.map((action) => {
        return (
          <Button
            size="small"
            type={type}
            onClick={clickHandler[action]}
            disabled={disabled[action]}
          >
            {text[action]}
          </Button>
        );
      })}
    </Container>
  );

  function onAddBatchClick() {}
  function onAddRecordClick() {}
  function onDeleteClick() {}
};

export default DatasetActions;
