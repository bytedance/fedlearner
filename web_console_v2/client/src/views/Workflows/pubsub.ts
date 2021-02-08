import PubSub from 'pubsub-js';

export const workflowPubsub = PubSub;

const WORKFLOW_CHANNELS = {
  create_new_tpl: 'workflow.create_new_tpl',
};

export default WORKFLOW_CHANNELS;
