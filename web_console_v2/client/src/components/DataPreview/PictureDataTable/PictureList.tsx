/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';
import GridRow from 'components/_base/GridRow';
import { ImageDetail } from 'typings/dataset';

const Container = styled.div`
  --cols: 6;

  display: grid;
  grid-template-columns: repeat(var(--cols), 1fr);
  align-items: start;
  justify-content: space-between;
  grid-gap: 15px;
  width: 100%;
  padding: 15px 20px;
  min-width: 550px;

  @media screen and (max-width: 1600px) {
    --cols: 5;
  }

  @media screen and (max-width: 1500px) {
    --cols: 4;
  }
`;

const CardContainer = styled.div`
  text-align: center;
`;
const Name = styled.div`
  color: var(--textColorStrongSecondary);
`;

const Size = styled.div`
  color: var(--textColorSecondary);
`;
const PictureContainer = styled(GridRow)`
  min-width: 88px;
  min-height: 88px;
  background-color: #f6f7fb;
  border-radius: 4px;
  cursor: pointer;
`;
const StyledImg = styled.img`
  height: 66px;
  width: 66px;
  border-radius: 5px;
  /* Crop the picture */
  object-fit: cover;
`;

const PictureCard: FC<{ data: ImageDetail; onClick?: (data: ImageDetail) => void }> = ({
  data,
  onClick,
}) => {
  return (
    <CardContainer>
      <PictureContainer
        justify="center"
        align="center"
        onClick={() => {
          onClick?.(data);
        }}
      >
        <StyledImg
          alt={data?.annotation?.caption || '照片显示错误'}
          src={data?.uri}
          title={data?.annotation?.caption}
        />
      </PictureContainer>
      <Name>{data.name}</Name>
      <Size>{`${data.width} × ${data.height}`}</Size>
    </CardContainer>
  );
};

const PictureList: FC<{ data: ImageDetail[]; onClick?: (data: ImageDetail) => void }> = ({
  data,
  onClick,
}) => {
  return (
    <Container>
      {data.map((item, index) => (
        <PictureCard data={item} key={`pic-${item.file_name}`} onClick={onClick} />
      ))}
    </Container>
  );
};

export default PictureList;
