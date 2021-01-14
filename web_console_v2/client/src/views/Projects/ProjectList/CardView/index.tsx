import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { Project } from 'typings/project';
import ProjectCard from './ProjectCard';

const Container = styled.div`
  --cols: 4;

  display: grid;
  grid-template-columns: repeat(var(--cols), 1fr);
  justify-content: space-between;
  grid-gap: 24px 20px;

  @media screen and (min-width: 1920px) and (max-width: 2560px) {
    --cols: 5;
  }

  @media screen and (max-width: 1440px) {
    --cols: 3;
  }

  @media screen and (max-width: 1200px) {
    --cols: 2;
  }

  @media screen and (max-width: 750px) {
    --cols: 1;
  }
`;

interface CardListProps {
  projectList: Project[];
}

function CardList({ projectList }: CardListProps): ReactElement {
  return (
    <Container>
      {projectList.map((item, index) => (
        <ProjectCard item={item} key={'p-' + index} />
      ))}
    </Container>
  );
}

export default CardList;
