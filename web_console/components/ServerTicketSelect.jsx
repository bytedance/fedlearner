import React from 'react';
import { Select, Popover, Code } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';

export default function ServerTicketSelect(props) {
  const { data } = useSWR(
    props.federation_id ? `federations/${props.federation_id}/tickets` : null,
    fetcher,
  );
  const tickets = (data && data.data) || [];
  const actualValue = tickets.find((x) => x.name === props.value)?.value;
  const actualOnChange = (value) => {
    const ticket = tickets.find((x) => x.name === value);
    props.onChange(ticket.name);
  };

  const popoverContent = (content) => {
    return (
      <pre className="content">
        {JSON.stringify(JSON.parse(content || '{}'), null, 2)}
        <style jsx>{`
          .content {
            color: #444;
            padding: 0 16px;
            min-width: 150px;
            max-height: 600px;
            max-width: 600px;
            overflow-wrap: break-word;
            overflow-y: scroll;
            overglow-x: hidden;
          }
        `}</style>
      </pre>
    )
  }

  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {
        tickets.map((x) =>
          <Select.Option key={x.name} value={x.name}>
            <Popover
              placement="left"
              offset={24}
              hideArrow={true}
              content={popoverContent(x.public_params)}
              trigger="hover"
            >
              {x.name}
            </Popover>
          </Select.Option>)
      }
    </Select>
  );
}
