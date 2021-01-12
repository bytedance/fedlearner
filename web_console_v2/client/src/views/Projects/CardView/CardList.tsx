import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { Project } from 'typings/project';
import ProjectCard from './ProjectCard';

const Container = styled.div`
  display: grid;
  grid-template-columns: repeat(3, minmax(272px, 371px));
  column-gap: 24px;
  row-gap: 24px;
  justify-content: space-between;

  // 272 * 4 + 24 * 3 + 24 * 2 + 200
  @media screen and (min-width: 1408px) {
    grid-template-columns: repeat(4, minmax(272px, 371px));
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
