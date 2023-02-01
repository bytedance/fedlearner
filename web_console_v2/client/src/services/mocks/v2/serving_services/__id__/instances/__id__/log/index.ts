const get = () => ({
  data: {
    data: [
      'I0917 01:00:57.550960      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'E0917 01:00:57.551087      51 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:00:57.549489      51 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'E0917 01:01:02.525449 1796675 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:01:02.525343 1796675 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'I0917 01:01:02.523937 1796675 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'I0917 01:01:07.503363 1796675 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'I0917 01:01:07.502001 1796675 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'I0917 01:01:12.521849      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'E0917 01:01:07.503472 1796675 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:01:12.520381      51 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'E0917 01:01:12.521968      51 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:01:22.641118      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'E0917 01:01:22.641228      51 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:01:22.639836      51 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'I0917 01:01:17.559534 1796675 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'I0917 01:01:17.560804 1796675 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 404 Not Found in 1 milliseconds',
      'E0917 01:01:17.560935 1796675 event_handler.go:225] RegisterHandler name = u11c2a27793c443c0888-nn-train-job, role = Follower, err = flapps.fedlearner.k8s.io "u11c2a27793c443c0888-nn-train-job" not found',
      'I0917 01:01:25.532047      51 controller.go:144] add new Pod u11c2a27793c443c0888-nn-train-job-leader-worker-0-e54b506a-b032-44f9-8919-247b781e8a24',
      'time="2021-09-17T01:01:25+08:00" level=info msg="Controller u11c2a27793c443c0888-nn-train-job created service u11c2a27793c443c0888-nn-train-job-leader-worker-0"',
      'I0917 01:01:25.545137      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:25.554689      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 8 milliseconds',
      'I0917 01:01:30.721617      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.475905      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreatePod\' Created pod: u11c2a27793c443c0888-nn-train-job-leader-master-0-34e8d5d8-37ca-458a-8f41-11351b57bc01',
      'I0917 01:01:25.545524      51 status_updater.go:115] updating flapp u11c2a27793c443c0888-nn-train-job status, namespace = fedlearner, new state = FLStateNew',
      'I0917 01:01:30.757848      51 app_manager.go:446] sync bootstrapped app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.500923      51 controller.go:144] add new Pod u11c2a27793c443c0888-nn-train-job-leader-ps-0-10a6ed31-a2c2-4512-9c8e-19622ace3061',
      'I0917 01:01:30.726261      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:25.476417      51 controller.go:144] add new Pod u11c2a27793c443c0888-nn-train-job-leader-master-0-34e8d5d8-37ca-458a-8f41-11351b57bc01',
      'I0917 01:01:25.533899      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreateService\' Created service: u11c2a27793c443c0888-nn-train-job-leader-master-0',
      'I0917 01:01:25.566288      51 status_updater.go:115] updating flapp u11c2a27793c443c0888-nn-train-job status, namespace = fedlearner, new state = FLStateNew',
      'I0917 01:01:25.581371      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:30.735962      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 9 milliseconds',
      'I0917 01:01:25.500580      51 pod_control.go:168] Controller u11c2a27793c443c0888-nn-train-job created pod u11c2a27793c443c0888-nn-train-job-leader-ps-0-10a6ed31-a2c2-4512-9c8e-19622ace3061',
      'I0917 01:01:25.565883      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:25.475794      51 pod_control.go:168] Controller u11c2a27793c443c0888-nn-train-job created pod u11c2a27793c443c0888-nn-train-job-leader-master-0-34e8d5d8-37ca-458a-8f41-11351b57bc01',
      'time="2021-09-17T01:01:25+08:00" level=info msg="Controller u11c2a27793c443c0888-nn-train-job created service u11c2a27793c443c0888-nn-train-job-leader-ps-0"',
      'I0917 01:01:25.531659      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreatePod\' Created pod: u11c2a27793c443c0888-nn-train-job-leader-worker-0-e54b506a-b032-44f9-8919-247b781e8a24',
      'I0917 01:01:25.537846      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreateService\' Created service: u11c2a27793c443c0888-nn-train-job-leader-worker-0',
      'I0917 01:01:30.757864      51 app_manager.go:456] sync bootstrapped leader app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.582708      51 round_trippers.go:443] PUT https://11.240.0.1:443/api/v1/namespaces/fedlearner/configmaps/u11c2a27793c443c0888-nn-train-job-leader-worker 200 OK in 1 milliseconds',
      'I0917 01:01:25.531550      51 pod_control.go:168] Controller u11c2a27793c443c0888-nn-train-job created pod u11c2a27793c443c0888-nn-train-job-leader-worker-0-e54b506a-b032-44f9-8919-247b781e8a24',
      'I0917 01:01:25.561049      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.665674      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.535827      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreateService\' Created service: u11c2a27793c443c0888-nn-train-job-leader-ps-0',
      'I0917 01:01:25.670023      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:30.723174      51 round_trippers.go:443] PUT https://11.240.0.1:443/api/v1/namespaces/fedlearner/configmaps/u11c2a27793c443c0888-nn-train-job-leader-worker 200 OK in 1 milliseconds',
      'I0917 01:01:30.742418      51 status_updater.go:115] updating flapp u11c2a27793c443c0888-nn-train-job status, namespace = fedlearner, new state = FLStateBootstrapped',
      'I0917 01:01:30.757875      51 app_manager.go:465] still waiting for follower, name = u11c2a27793c443c0888-nn-train-job, rtype = Worker',
      'I0917 01:01:25.442789      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:30.742349      51 app_manager.go:229] sync new app, name = u11c2a27793c443c0888-nn-train-job',
      'I0917 01:01:25.574974      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 8 milliseconds',
      'I0917 01:01:30.751224      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 8 milliseconds',
      'I0917 01:01:25.500690      51 event.go:278] Event(v1.ObjectReference{Kind:"FLApp", Namespace:"fedlearner", Name:"u11c2a27793c443c0888-nn-train-job", UID:"3d5acdf9-9b45-470e-b8df-e6a70f28b8f1", APIVersion:"fedlearner.k8s.io/v1alpha1", ResourceVersion:"987444923", FieldPath:""}): type: \'Normal\' reason: \'SuccessfulCreatePod\' Created pod: u11c2a27793c443c0888-nn-train-job-leader-ps-0-10a6ed31-a2c2-4512-9c8e-19622ace3061',
      'I0917 01:01:30.726664      51 status_updater.go:115] updating flapp u11c2a27793c443c0888-nn-train-job status, namespace = fedlearner, new state = FLStateNew',
      'time="2021-09-17T01:01:25+08:00" level=info msg="Controller u11c2a27793c443c0888-nn-train-job created service u11c2a27793c443c0888-nn-train-job-leader-master-0"',
      'I0917 01:01:25.585747      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:25.667049      51 round_trippers.go:443] PUT https://11.240.0.1:443/api/v1/namespaces/fedlearner/configmaps/u11c2a27793c443c0888-nn-train-job-leader-worker 200 OK in 1 milliseconds',
      'E0917 01:01:30.757881      51 controller.go:225] failed to sync FLApp fedlearner/u11c2a27793c443c0888-nn-train-job, err = still waiting for follower, name = u11c2a27793c443c0888-nn-train-job, rtype = Worker',
      'I0917 01:01:25.562610      51 round_trippers.go:443] PUT https://11.240.0.1:443/api/v1/namespaces/fedlearner/configmaps/u11c2a27793c443c0888-nn-train-job-leader-worker 200 OK in 1 milliseconds',
      'E0917 01:01:27.805979 1796675 event_handler.go:233] RegisterHandler leader is not bootstrapped, name = u11c2a27793c443c0888-nn-train-job, role = Follower, state = FLStateNew',
      'I0917 01:01:27.802569 1796675 server.go:49] Register received, name = u11c2a27793c443c0888-nn-train-job, role = Follower',
      'I0917 01:01:27.805507 1796675 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:33.123219      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:33.200786      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
      'I0917 01:01:33.226327      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 9 milliseconds',
      'I0917 01:01:33.210341      51 round_trippers.go:443] PUT https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job/status 200 OK in 8 milliseconds',
      'I0917 01:01:33.242903      51 round_trippers.go:443] GET https://11.240.0.1:443/apis/fedlearner.k8s.io/v1alpha1/namespaces/fedlearner/flapps/u11c2a27793c443c0888-nn-train-job 200 OK in 2 milliseconds',
    ],
  },
  status: 200,
});

export default get;
