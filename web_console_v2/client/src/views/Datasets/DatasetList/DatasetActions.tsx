import React, { FC } from 'react';
import styled from 'styled-components';
import { Dataset, DatasetType } from 'typings/dataset';
import GridRow from 'components/_base/GridRow';
import { useTranslation } from 'react-i18next';
import { Button } from 'antd';
import { isImportFailed } from 'shared/dataset';
import { ButtonType } from 'antd/lib/button';

const Container = styled(GridRow)`
  margin-left: ${(props: any) => (props.type === 'link' ? '-15px !important' : 0)};

  > .hide-on-bush {
    visibility: hidden;
    pointer-events: none;
  }
`;

export type DatasetAction = 'add-batch' | 'view-records' | 'delete' | 'copy-path';
type Props = {
  dataset: Dataset;
  type: ButtonType;
  onPerformAction: (args: { action: DatasetAction; dataset: Dataset }) => void;
};

const actions: DatasetAction[] = ['add-batch', 'view-records', 'copy-path', 'delete'];

const DatasetActions: FC<Props> = ({ dataset, type = 'default', onPerformAction }) => {
  const { t } = useTranslation();

  const disabled: Record<DatasetAction, boolean> = {
    'add-batch': isImportFailed(dataset),
    'view-records': false,
    'copy-path': false,
    delete: false,
  };
  const visible = {
    'add-batch': dataset.dataset_type === DatasetType.STREAMING,
    'view-records': true,
    'copy-path': true,
    delete: true,
  };
  const text = {
    'add-batch': t('dataset.btn_add_batch'),
    'view-records': t('dataset.btn_view_records'),
    'copy-path': t('dataset.btn_copy_path'),
    delete: t('delete'),
  };

  return (
    <Container {...{ type }}>
      {actions.map((action) => {
        return (
          <Button
            size="small"
            type={type}
            key={action}
            danger={action === 'delete'}
            onClick={() => onPerformAction({ action, dataset })}
            disabled={disabled[action]}
            className={!visible[action] ? 'hide-on-bush' : ''}
          >
            {text[action]}
          </Button>
        );
      })}
    </Container>
  );
};

export default DatasetActions;
