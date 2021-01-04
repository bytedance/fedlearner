import React, { FunctionComponent } from 'react'
import styled from 'styled-components'
import { MixinCircle, MixinSquare } from 'styles/mixins'

const Container = styled.div`
  &::before {
    content: '';
    display: inline-block;
  }

  &::after {
    content: ${(props: Props) => (props.desc ? 'attr(data-desc)' : null)};
    padding-left: 5px;
  }
`

const WritableShape = styled(Container)`
  &::before {
    width: 14px;
    height: 11px;
    background-color: var(--primaryColor);
    clip-path: polygon(50% 0, 100% 100%, 0 100%, 50% 0);
  }
`
const ReadableShape = styled(Container)`
  &::before {
    ${MixinSquare(11)};

    background-color: var(--successColor);
  }
`
const PrivateShape = styled(Container)`
  &::before {
    ${MixinCircle(12)};

    background-color: var(--warningColor);
  }
`

type Props = {
  desc?: boolean
}

const Writable: FunctionComponent<Props> = (props) => {
  return <WritableShape {...props} data-desc="可编辑" />
}

const Readable: FunctionComponent<Props> = (props) => {
  return <ReadableShape {...props} data-desc="可见" />
}

const Private: FunctionComponent<Props> = (props) => {
  return <PrivateShape {...props} data-desc="不可见" />
}

const VariablePermission = { Writable, Readable, Private }

export default VariablePermission
