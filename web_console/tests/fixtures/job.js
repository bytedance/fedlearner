module.exports = {
  leader: {
    name: 'leader_job',
    k8s_name: 'leader_job',
    job_type: 'data_join',
    client_ticket_name: 'leader_ticket',
    server_ticket_name: 'follower_ticket',
    client_params: {},
    server_params: {},
  },
  follower: {
    name: 'follower_job',
    k8s_name: 'follower_job',
    job_type: 'data_join',
    client_ticket_name: 'follower_ticket',
    server_ticket_name: 'leader_ticket',
    client_params: {},
    server_params: {},
  },
  test: {
    name: 'test_job',
    k8s_name: 'test_job',
    job_type: 'psi_data_join',
    client_ticket_name: 'leader_ticket',
    server_ticket_name: 'follower_ticket',
    client_params: {},
    server_params: {},
  },
};
