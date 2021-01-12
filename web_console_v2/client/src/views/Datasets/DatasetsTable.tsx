import React, { FunctionComponent } from 'react';
import ListPageLayout from 'components/ListPageLayout';
import { useTranslation } from 'react-i18next';

const DatasetsTable: FunctionComponent = () => {
  const { t } = useTranslation();

  return <ListPageLayout title={t('term.dataset')}>placeholder</ListPageLayout>;
};

export default DatasetsTable;
