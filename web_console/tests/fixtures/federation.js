module.exports = {
  leader: {
    name: 'leader',
    trademark: 'Leader',
    email: 'fl@leader.com',
    tel: null,
    avatar: 'https://fl.com/leader.png',
    k8s_settings: {
      grpc_spec: {
        peerURL: 'localhost:1990',
        authority: 'leader',
        extraHeaders: {
          'x-host': 'leader.flapp.web_console',
          'x-federation': 'follower',
        },
      },
    },
  },
  follower: {
    name: 'follower',
    trademark: 'Follower',
    email: 'fl@follower.com',
    tel: null,
    avatar: 'https://fl.com/follower.png',
    k8s_settings: {
      grpc_spec: {
        peerURL: 'localhost:1990',
        authority: 'follower',
        extraHeaders: {
          'x-host': 'follower.flapp.web_console',
          'x-federation': 'leader',
        },
      },
    },
  },
};
