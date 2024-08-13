const get = (config: any) => {
  return {
    data: {
      data: {
        id: 13,
        name: 'u0d81863120e64c35aae-raw-data-job',
        job_type: 'RAW_DATA',
        state: 'FAILED',
        is_disabled: false,
        workflow_id: 4,
        project_id: 1,
        flapp_snapshot: null,
        sparkapp_snapshot: null,
        snapshot:
          '{"app": {"status": {"appState": "FLStateShutDown", "completionTime": null, "flReplicaStatus": {"Master": {"active": {}, "failed": {"u0d81863120e64c35aae-raw-data-job-follower-master-0-0fa05dfb-0ce1-40da-894b-69af79223197": {}, "u0d81863120e64c35aae-raw-data-job-follower-master-0-20581ad4-d24a-4b20-9958-e7b0c979b24e": {}, "u0d81863120e64c35aae-raw-data-job-follower-master-0-39116f42-0cad-484a-8c37-7424b5084626": {}, "u0d81863120e64c35aae-raw-data-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6": {}, "u0d81863120e64c35aae-raw-data-job-follower-master-0-b741750c-efbb-4893-adb5-838d7fdcddff": {}, "u0d81863120e64c35aae-raw-data-job-follower-master-0-c5610c81-1b7b-4180-85fd-6e065f538bc9": {}}, "local": {"u0d81863120e64c35aae-raw-data-job-follower-master-0": {}}, "mapping": {}, "remote": {}, "succeeded": {}}, "Worker": {"active": {}, "failed": {"u0d81863120e64c35aae-raw-data-job-follower-worker-0-cc2ecf1f-011f-4b36-98cb-dcac561ca6bf": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-1-f9d2835f-eeca-4a88-89d0-9694904b48bd": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-2-90e2ee0e-ba90-4d5b-b841-b894a17533cd": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-3-bca627c6-2c72-4e26-82bc-bd0e1a131ae2": {}}, "local": {"u0d81863120e64c35aae-raw-data-job-follower-worker-0": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-1": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-2": {}, "u0d81863120e64c35aae-raw-data-job-follower-worker-3": {}}, "mapping": {}, "remote": {}, "succeeded": {}}}}}, "pods": {"items": [{"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:41+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:41+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://f96c6294df7efc5e5e46d83fae462ed0512b26d96946c306e062265a2b05380b", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://f96c6294df7efc5e5e46d83fae462ed0512b26d96946c306e062265a2b05380b", "exit_code": 1, "finished_at": "2022-04-21T08:41:41+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:41:35+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.64", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.228", "pod_i_ps": [{"ip": "172.20.1.228"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:33+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:33+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:41:44+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-b741750c-efbb-4893-adb5-838d7fdcddff", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982405396", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-b741750c-efbb-4893-adb5-838d7fdcddff", "uid": "cf8adcce-4344-4777-8c3d-f6c7f47971dc"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:34+00:00", "message": null, "reason": null, "status": "True", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:34+00:00", "message": null, "reason": null, "status": "True", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://4a2d516148b8d0457cd144fada8e39fa6b02cf6698d74ec5fcc351add764a4b6", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": true, "restart_count": 0, "started": true, "state": {"running": {"started_at": "2022-04-21T08:41:34+00:00"}, "terminated": null, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.57", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Running", "pod_ip": "172.20.0.222", "pod_i_ps": [{"ip": "172.20.0.222"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:33+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:33+00:00", "deletion_grace_period_seconds": null, "deletion_timestamp": null, "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "worker", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-worker-0-cc2ecf1f-011f-4b36-98cb-dcac561ca6bf", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982404984", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-worker-0-cc2ecf1f-011f-4b36-98cb-dcac561ca6bf", "uid": "03fdb82a-a9d7-4280-8c13-013676e9a752"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://eca6aecd645b52dea03dfc2d64535ae33f1c78b39ae056299f5e9ff6bbf9a789", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": true, "restart_count": 0, "started": true, "state": {"running": {"started_at": "2022-04-21T08:41:34+00:00"}, "terminated": null, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.62", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Running", "pod_ip": "172.20.2.93", "pod_i_ps": [{"ip": "172.20.2.93"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:33+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:33+00:00", "deletion_grace_period_seconds": null, "deletion_timestamp": null, "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "1", "fl-replica-type": "worker", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-worker-1-f9d2835f-eeca-4a88-89d0-9694904b48bd", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982405009", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-worker-1-f9d2835f-eeca-4a88-89d0-9694904b48bd", "uid": "c2fb28d9-43ae-4ab3-988c-54dacfc2037c"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://db00170b8d2ab93a5541e8207e94bdfe9fcc415b8d6742993c6cb970cac9fe0a", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": true, "restart_count": 0, "started": true, "state": {"running": {"started_at": "2022-04-21T08:41:34+00:00"}, "terminated": null, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.60", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Running", "pod_ip": "172.20.1.167", "pod_i_ps": [{"ip": "172.20.1.167"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:33+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:33+00:00", "deletion_grace_period_seconds": null, "deletion_timestamp": null, "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "2", "fl-replica-type": "worker", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-worker-2-90e2ee0e-ba90-4d5b-b841-b894a17533cd", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982405014", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-worker-2-90e2ee0e-ba90-4d5b-b841-b894a17533cd", "uid": "5c39edb3-f34b-47c6-9a7b-c86f1377982a"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:35+00:00", "message": null, "reason": null, "status": "True", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:33+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://ee4c255a9a0bcf865f0fcc9b8f3fd06817cfc45037525f998e77f50af62b0c1a", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": true, "restart_count": 0, "started": true, "state": {"running": {"started_at": "2022-04-21T08:41:34+00:00"}, "terminated": null, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.64", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Running", "pod_ip": "172.20.1.227", "pod_i_ps": [{"ip": "172.20.1.227"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:33+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:33+00:00", "deletion_grace_period_seconds": null, "deletion_timestamp": null, "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "3", "fl-replica-type": "worker", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-worker-3-bca627c6-2c72-4e26-82bc-bd0e1a131ae2", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982405032", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-worker-3-bca627c6-2c72-4e26-82bc-bd0e1a131ae2", "uid": "45506ffd-82c7-464d-8e0d-a1003ce5c7f8"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:44+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:52+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:52+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:44+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://d3d7d35423c1da5822bf6edd311ec63e36b12f9c4e0e902d21db3ca0f5f274bb", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://d3d7d35423c1da5822bf6edd311ec63e36b12f9c4e0e902d21db3ca0f5f274bb", "exit_code": 1, "finished_at": "2022-04-21T08:41:52+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:41:45+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.59", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.94", "pod_i_ps": [{"ip": "172.20.1.94"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:44+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:44+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:41:54+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-c5610c81-1b7b-4180-85fd-6e065f538bc9", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982405829", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-c5610c81-1b7b-4180-85fd-6e065f538bc9", "uid": "25066279-22f4-4a54-af52-e7b73b85ec13"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:54+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:03+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:03+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:41:54+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://47f1bd13a385a28028977d590b23bc33246277aac34b7d2835b3dd7efd582a4a", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://47f1bd13a385a28028977d590b23bc33246277aac34b7d2835b3dd7efd582a4a", "exit_code": 1, "finished_at": "2022-04-21T08:42:02+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:41:55+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.59", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.95", "pod_i_ps": [{"ip": "172.20.1.95"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:41:54+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:41:54+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:42:04+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-0fa05dfb-0ce1-40da-894b-69af79223197", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982406271", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-0fa05dfb-0ce1-40da-894b-69af79223197", "uid": "6fe1044e-e13d-4206-b9b4-6de1c52df48a"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:04+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:13+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:13+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:04+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://ef5b213dc9b879cf8a5cf14dd6af4b86f066f73a7c21479bc8e87ff3e68c6924", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://ef5b213dc9b879cf8a5cf14dd6af4b86f066f73a7c21479bc8e87ff3e68c6924", "exit_code": 1, "finished_at": "2022-04-21T08:42:12+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:42:05+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.59", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.96", "pod_i_ps": [{"ip": "172.20.1.96"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:42:04+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:42:04+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:42:14+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-39116f42-0cad-484a-8c37-7424b5084626", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982406709", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-39116f42-0cad-484a-8c37-7424b5084626", "uid": "d7283a7a-a66e-427a-bfe9-12c5542bc43e"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:14+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:23+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:23+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:14+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://c0fc917668d5f3e8fbbf6b6fecee660bba3df7faaf9ce248f61985ca16484da0", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://c0fc917668d5f3e8fbbf6b6fecee660bba3df7faaf9ce248f61985ca16484da0", "exit_code": 1, "finished_at": "2022-04-21T08:42:22+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:42:15+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.59", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.97", "pod_i_ps": [{"ip": "172.20.1.97"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:42:14+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:42:14+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:42:24+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-20581ad4-d24a-4b20-9958-e7b0c979b24e", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982407144", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-20581ad4-d24a-4b20-9958-e7b0c979b24e", "uid": "9b466c64-f70c-4449-ba34-f094200f3309"}}, {"status": {"conditions": [{"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:24+00:00", "message": null, "reason": null, "status": "True", "type": "Initialized"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:32+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "Ready"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:32+00:00", "message": "containers with unready status: [tensorflow]", "reason": "ContainersNotReady", "status": "False", "type": "ContainersReady"}, {"last_probe_time": null, "last_transition_time": "2022-04-21T08:42:24+00:00", "message": null, "reason": null, "status": "True", "type": "PodScheduled"}], "container_statuses": [{"container_id": "docker://de5ed97e5c40861378439814230db66654d54e88668e93e6379908d3a2a2f2f8", "image": "artifact.bytedance.com/fedlearner/fedlearner:882310f", "image_id": "docker-pullable://artifact.bytedance.com/fedlearner/fedlearner@sha256:170c117f8615b53372b5b8e3aaec14997f3d5a77c3921824ecc24f5b99dbf577", "last_state": {"running": null, "terminated": null, "waiting": null}, "name": "tensorflow", "ready": false, "restart_count": 0, "started": false, "state": {"running": null, "terminated": {"container_id": "docker://de5ed97e5c40861378439814230db66654d54e88668e93e6379908d3a2a2f2f8", "exit_code": 1, "finished_at": "2022-04-21T08:42:32+00:00", "message": null, "reason": "Error", "signal": null, "started_at": "2022-04-21T08:42:25+00:00"}, "waiting": null}}], "ephemeral_container_statuses": null, "host_ip": "192.168.252.59", "init_container_statuses": null, "message": null, "nominated_node_name": null, "phase": "Failed", "pod_ip": "172.20.1.98", "pod_i_ps": [{"ip": "172.20.1.98"}], "qos_class": "Guaranteed", "reason": null, "start_time": "2022-04-21T08:42:24+00:00"}, "metadata": {"annotations": {"kubernetes.io/psp": "ack.privileged"}, "cluster_name": null, "creation_timestamp": "2022-04-21T08:42:24+00:00", "deletion_grace_period_seconds": 0, "deletion_timestamp": "2022-04-21T08:42:34+00:00", "finalizers": null, "generate_name": null, "generation": null, "labels": {"app-name": "u0d81863120e64c35aae-raw-data-job", "fl-replica-index": "0", "fl-replica-type": "master", "role": "follower"}, "managed_fields": null, "name": "u0d81863120e64c35aae-raw-data-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6", "namespace": "default", "owner_references": [{"api_version": "fedlearner.k8s.io/v1alpha1", "block_owner_deletion": true, "controller": true, "kind": "FLApp", "name": "u0d81863120e64c35aae-raw-data-job", "uid": "620e92c7-0842-41dd-8eff-cf9c7e010b6b"}], "resource_version": "2982407585", "self_link": "/api/v1/namespaces/default/pods/u0d81863120e64c35aae-raw-data-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6", "uid": "b739e218-6b15-4c7b-b2d3-cddd30ddd370"}}], "deleted": false}}',
        error_message: null,
        crd_meta: 'api_version: "fedlearner.k8s.io/v1alpha1"\n',
        crd_kind: 'FLApp',
        created_at: 1650530491,
        updated_at: 1650530554,
        deleted_at: null,
        complete_at: 0,
        pods: [
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-b741750c-efbb-4893-adb5-838d7fdcddff',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.228',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530493,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-worker-0-cc2ecf1f-011f-4b36-98cb-dcac561ca6bf',
            pod_type: 'WORKER',
            state: 'RUNNING',
            pod_ip: '172.20.0.222',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530493,
            message: '',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-worker-1-f9d2835f-eeca-4a88-89d0-9694904b48bd',
            pod_type: 'WORKER',
            state: 'RUNNING',
            pod_ip: '172.20.2.93',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530493,
            message: '',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-worker-2-90e2ee0e-ba90-4d5b-b841-b894a17533cd',
            pod_type: 'WORKER',
            state: 'RUNNING',
            pod_ip: '172.20.1.167',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530493,
            message: '',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-worker-3-bca627c6-2c72-4e26-82bc-bd0e1a131ae2',
            pod_type: 'WORKER',
            state: 'RUNNING',
            pod_ip: '172.20.1.227',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530493,
            message: '',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-c5610c81-1b7b-4180-85fd-6e065f538bc9',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.94',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530504,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-0fa05dfb-0ce1-40da-894b-69af79223197',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.95',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530514,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-39116f42-0cad-484a-8c37-7424b5084626',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.96',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530524,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-20581ad4-d24a-4b20-9958-e7b0c979b24e',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.97',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530534,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.98',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530544,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-a-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.98',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530544,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-mar-0-3e89045e-52ff-4457-ab0d-7a917d2278c6',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.98',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530544,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64aae-raw-data-job-follower-master-0-3e89045e-52ff-4457-ab0d-7a917d2278c6',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.98',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530544,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
          {
            name:
              'u0d81863120e64c35aae-raw-data-job-follower-mas-0-3e89045e-52ff-4457-ab0d-7a917d2278c6',
            pod_type: 'MASTER',
            state: 'FAILED_AND_FREED',
            pod_ip: '172.20.1.98',
            limits_cpu: '',
            limits_memory: '',
            requests_cpu: '',
            requests_memory: '',
            creation_timestamp: 1650530544,
            message:
              'terminated:Error, Ready:containers with unready status: [tensorflow], ContainersReady:containers with unready status: [tensorflow]',
          },
        ],
      },
    },
    status: 200,
  };
};

export default get;
