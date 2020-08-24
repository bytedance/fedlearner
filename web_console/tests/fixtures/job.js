module.exports = {
  leader: {
    name: 'leader-job',
    job_type: 'data_join',
    client_ticket_name: 'leader_ticket',
    server_ticket_name: 'follower_ticket',
    client_params: {},
    server_params: {},
  },
  follower: {
    name: 'follower-job',
    job_type: 'data_join',
    client_ticket_name: 'follower_ticket',
    server_ticket_name: 'leader_ticket',
    client_params: {},
    server_params: {},
  },
  test: {
    name: 'test-job',
    job_type: 'psi_data_join',
    client_ticket_name: 'leader_ticket',
    server_ticket_name: 'follower_ticket',
    client_params: {},
    server_params: {},
  },
};
