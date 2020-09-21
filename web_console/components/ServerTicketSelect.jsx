import React from 'react';
import { Select, Popover, Code } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';
import { JOB_TYPE } from '../constants/job'

// const mockRes = {
//   "data": [
//     {
//       "name": "ticket-360-k4",
//       "job_type": "data_join",
//       "role": "Follower",
//       "sdk_version": "049ad50",
//       "expire_time": "Fri Jun 18 2021 00:00:00 GMT+0000 (Coordinated Universal Time)",
//       "remark": "",
//       "public_params": "null"
//     },
//     {
//       "name": "test-training",
//       "job_type": "nn_model",
//       "role": "Follower",
//       "sdk_version": "049ad50",
//       "expire_time": "Fri Jun 18 2021 00:00:00 GMT+0000 (Coordinated Universal Time)",
//       "remark": "",
//       "public_params": "null"
//     }
//   ]
// }

let filter = () => true
export default function ServerTicketSelect({type, ...props}) {

  if (type) {
    filter = el => JOB_TYPE[type].some(t => el.job_type === t)
  }

  const { data } = useSWR(
    props.federation_id ? `federations/${props.federation_id}/tickets` : null,
    fetcher,
  );
  const tickets = data?.data?.filter(filter) || []
  // const tickets = mockRes.data;

  const actualValue = tickets.find((x) => x.name === props.value)?.name;
  const actualOnChange = (value) => {
    const ticket = tickets.find((x) => x.name === value);
    props.onChange(ticket.name);
  };

  const popoverContent = (content) => {
    if (typeof content.public_params === 'string') {
      content.public_params = JSON.parse(content.public_params || '{}')
    }
    return (
      <pre className="content">
        {JSON.stringify(content, null, 2)}
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
              content={popoverContent(x)}
              trigger="hover"
            >
              {x.name}
            </Popover>
          </Select.Option>)
      }
    </Select>
  );
}
