import React from 'react';
import { Select, Popover, Code } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';
import { JOB_TYPE } from '../constants/job'

const mockRes = {
  "data": [
    {
      "name": "falin-join-20200827",
      "job_type": "psi_data_join",
      "role": "Follower",
      "sdk_version": "c50be61",
      "expire_time": "",
      "remark": "",
      "public_params": "{\"spec\":{\"flReplicaSpecs\":{\"Master\":{\"pair\":true,\"template\":{\"spec\":{\"containers\":[{\"env\":[{\"name\":\"PARTITION_NUM\",\"value\":\"2\"},{\"name\":\"START_TIME\",\"value\":\"0\"},{\"name\":\"END_TIME\",\"value\":\"999999999999\"},{\"name\":\"NEGATIVE_SAMPLING_RATE\",\"value\":\"1.0\"},{\"name\":\"RAW_DATA_SUB_DIR\",\"value\":\"psi_data_join/falin-20200828\"}],\"image\":\"artifact.bytedance.com/fedlearner/fedlearner:c50be61\",\"ports\":[{\"containerPort\":50051,\"name\":\"flapp-port\"}],\"command\":[\"/app/deploy/scripts/wait4pair_wrapper.sh\"],\"args\":[\"/app/deploy/scripts/data_join/run_data_join_leader_master.sh\"]}]}}},\"Worker\":{\"pair\":true,\"template\":{\"spec\":{\"containers\":[{\"env\":[{\"name\":\"PSI_RAW_DATA_ITER\",\"value\":\"CSV_DICT\"},{\"name\":\"PSI_OUTPUT_BUILDER\",\"value\":\"CSV_DICT\"},{\"name\":\"DATA_BLOCK_BUILDER\",\"value\":\"CSV_DICT\"},{\"name\":\"DATA_BLOCK_DUMP_INTERVAL\",\"value\":\"600\"},{\"name\":\"DATA_BLOCK_DUMP_THRESHOLD\",\"value\":\"524288\"},{\"name\":\"EXAMPLE_ID_DUMP_INTERVAL\",\"value\":\"600\"},{\"name\":\"EXAMPLE_ID_DUMP_THRESHOLD\",\"value\":\"524288\"},{\"name\":\"EXAMPLE_JOINER\",\"value\":\"SORT_RUN_JOINER\"},{\"name\":\"INPUT_FILE_SUBSCRIBE_DIR\",\"value\":\"portal_publish_dir/falin-test-20200827-follower\"},{\"name\":\"RAW_DATA_PUBLISH_DIR\",\"value\":\"psi_data_join/falin-20200828\"},{\"name\":\"RSA_KEY_PATH\",\"value\":\"/data/rsa_key/test_rsa_psi.pub\"},{\"name\":\"SIGN_RPC_TIMEOUT_MS\",\"value\":\"128000\"}],\"image\":\"artifact.bytedance.com/fedlearner/fedlearner:c50be61\",\"ports\":[{\"containerPort\":50051,\"name\":\"flapp-port\"}],\"command\":[\"/app/deploy/scripts/wait4pair_wrapper.sh\"],\"args\":[\"/app/deploy/scripts/data_join/run_psi_data_join_follower_worker_v2.sh\"]}]}}}}}}"
    }
  ]
}

let filter = () => true
export default function ServerTicketSelect({type, ...props}) {

  if (type) {
    filter = el => JOB_TYPE[type].some(t => el.job_type === t)
  }

  const { data } = useSWR(
    props.federation_id ? `federations/${props.federation_id}/tickets` : null,
    fetcher,
  );
  const tickets = data?.data?.filter(filter) || mockRes.data;

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
