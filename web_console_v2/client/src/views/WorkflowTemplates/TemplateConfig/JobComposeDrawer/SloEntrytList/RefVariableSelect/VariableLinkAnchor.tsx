import React, { FC } from 'react';
import { AnchorIcon } from '../../elements';
import IconButton from 'components/IconButton';
import { Grid, Tooltip } from '@arco-design/web-react';
import { COMPOSE_DRAWER_CHANNELS } from '../..';

const Col = Grid.Col;

export type InspetVariableParams = {
  jobUuid?: string;
  varUuid: string;
  disabled?: boolean;
};

type Props = InspetVariableParams;

const VariableLinkAnchor: FC<Props> = ({ jobUuid, varUuid, disabled }) => {
  return (
    <Col style={{ flex: '1' }}>
      <Tooltip content={'查看变量'}>
        <IconButton
          disabled={disabled}
          style={{ width: '100%', height: '100%' }}
          icon={<AnchorIcon style={{ marginLeft: 0 }} />}
          onClick={inspectVariable}
        />
      </Tooltip>
    </Col>
  );

  function inspectVariable() {
    PubSub.publish(COMPOSE_DRAWER_CHANNELS.inspect, { jobUuid, varUuid });
  }
};

export default VariableLinkAnchor;
