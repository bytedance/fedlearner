import React, { FC, useMemo } from 'react';
import styled from 'styled-components';
import { Tag, TagProps } from '@arco-design/web-react';
import { EnumAlgorithmProjectType } from 'typings/algorithm';

type Props = {
  style?: React.CSSProperties;
  type: EnumAlgorithmProjectType;
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

const AlgorithmType: FC<Props> = ({ style = {}, type, tagProps = {} }) => {
  const [tagName, modelName] = useMemo(() => {
    if (type === EnumAlgorithmProjectType.UNSPECIFIED) {
      return ['自定义算法', ''];
    }

    const [modelType, federalType] = type.split('_');
    let tagName = '';
    let modelName = '';

    if (federalType) {
      switch (federalType) {
        case 'VERTICAL':
          tagName = '纵向联邦';
          break;
        case 'HORIZONTAL':
          tagName = '横向联邦';
          break;
        case 'COMPUTING':
          tagName = '可信计算';
          break;
        default:
          tagName = '-';
          break;
      }
    }

    if (modelType) {
      switch (modelType) {
        case 'NN':
          modelName = 'NN模型';
          break;
        case 'TREE':
          modelName = '树模型';
          break;
        case 'TRUSTED':
          modelName = '';
          break;
      }
    }

    return [tagName, modelName];
  }, [type]);

  const mergedTagStyle = useMemo<React.CSSProperties>(() => {
    return {
      fontWeight: 'normal',
      ...(tagProps.style ?? {}),
    };
  }, [tagProps.style]);

  return (
    <Container style={style}>
      {tagName ? (
        <StyledModalTag {...tagProps} style={mergedTagStyle}>
          {tagName}
          {modelName ? `-${modelName}` : ''}
        </StyledModalTag>
      ) : (
        ''
      )}
    </Container>
  );
};

export default AlgorithmType;
