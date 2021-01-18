import React, { ReactElement, useRef, useState } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { Tooltip } from 'antd';
import { MixinEllipsis } from 'styles/mixins';
import { useMount } from 'react-use';

const Container = styled.div`
  ${MixinEllipsis()}

  color: var(--gray10);
  font-weight: 500;
  font-size: 15px;
  line-height: 40px;
  margin-left: 16px;
`;

interface CreateTimeProps {
  text: string;
  style?: CSSProperties;
}

function ProjectName({ text, style }: CreateTimeProps): ReactElement {
  const eleRef = useRef<HTMLDivElement>();
  const [trigger, setTrigger] = useState('click');
  useMount(() => {
    // Check element overflow at next-tick
    setImmediate(() => {
      const { current } = eleRef;
      if (current) {
        if (current.scrollWidth > current.offsetWidth) {
          setTrigger('hover');
        }
      }
    });
  });
  return (
    <Tooltip title={text} trigger={trigger}>
      <Container ref={eleRef as any} style={style}>
        {text}
      </Container>
    </Tooltip>
  );
}

export default ProjectName;
