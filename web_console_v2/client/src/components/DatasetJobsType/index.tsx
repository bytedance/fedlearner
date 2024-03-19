import React, { FC, useMemo } from 'react';
import styled from 'styled-components';
import { Tag, TagProps } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import { DataJobBackEndType } from 'typings/dataset';

type Props = {
  style?: React.CSSProperties;
  type: DataJobBackEndType;
  tagProps?: Partial<TagProps>;
};

const Container = styled.div`
  display: inline-block;
`;
const StyledModalTag = styled(Tag)`
  margin-right: 4px;
  font-size: 12px;
  vertical-align: top;
`;

const DatasetJobsType: FC<Props> = ({ style = {}, type, tagProps = {} }) => {
  const { t } = useTranslation();
  const [taskType, tagColor]: string[] = useMemo(() => {
    if (!type) {
      return ['jobType error: type empty'];
    }
    switch (type) {
      case DataJobBackEndType.DATA_JOIN:
      case DataJobBackEndType.RSA_PSI_DATA_JOIN:
      case DataJobBackEndType.OT_PSI_DATA_JOIN:
      case DataJobBackEndType.LIGHT_CLIENT_RSA_PSI_DATA_JOIN:
      case DataJobBackEndType.LIGHT_CLIENT_OT_PSI_DATA_JOIN:
      case DataJobBackEndType.HASH_DATA_JOIN:
        return [t('dataset.label_data_job_type_create'), 'arcoblue'];
      case DataJobBackEndType.DATA_ALIGNMENT:
        return [t('dataset.label_data_job_type_alignment'), 'arcoblue'];
      case DataJobBackEndType.IMPORT_SOURCE:
        return [t('dataset.label_data_job_type_import')];
      case DataJobBackEndType.EXPORT:
        return [t('dataset.label_data_job_type_export')];
      case DataJobBackEndType.ANALYZER:
        return ['数据探查'];
      default:
        return ['jobType error: unknown type'];
    }
  }, [t, type]);

  const mergedTagStyle = useMemo<React.CSSProperties>(() => {
    return {
      fontWeight: 'normal',
      ...(tagProps.style ?? {}),
    };
  }, [tagProps.style]);

  return (
    <Container style={style}>
      <StyledModalTag {...{ ...tagProps, color: tagColor }} style={mergedTagStyle}>
        {taskType}
      </StyledModalTag>
    </Container>
  );
};

export default DatasetJobsType;
