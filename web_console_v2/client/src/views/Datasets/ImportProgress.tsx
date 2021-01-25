import React, { FC } from 'react';
import styled from 'styled-components';
import { Dataset } from 'typings/dataset';
import StateIndicator from 'components/StateIndicator';
import { getImportedProportion, getImportStage, isImporting } from 'shared/dataset';

const ProgressBar = styled.div`
  position: relative;
  width: 100px;
  height: 4px;
  margin-top: 5px;
  margin-left: 15px;
  border-radius: 10px;
  background-color: var(--backgroundGray);
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    width: inherit;
    height: inherit;
    border-radius: inherit;
    background-color: var(--primaryColor);
    transform: translateX(var(--progress));
  }
`;

const ImportProgress: FC<{ dataset: Dataset }> = ({ dataset }) => {
  const { total, imported } = getImportedProportion(dataset);
  const proportion = Math.floor((imported / total) * 100);

  return (
    <div>
      <StateIndicator {...getImportStage(dataset)} />
      {isImporting(dataset) && (
        <ProgressBar style={{ '--progress': `${proportion - 100}%` } as any} />
      )}
    </div>
  );
};

export default ImportProgress;
