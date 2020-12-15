class WorkflowGrpc:
    def _grpc_update_workflow(self, uid, status, project_token, name=None, forkable=None, config=None,
                              peer_config=None, can_create=False):
        """
        CREATE_PREPARE_SENDER = 1
        CREATE_PREPARE_RECEIVER = 2
        CREATE_COMMITTABLE_SENDER = 3
        CREATE_COMMITTABLE_RECEIVER  = 4
        CREATED = 5

        config should be binary-byte string.
        """
        # TODO:
        pass

    def create_workflow(self, uid, name, config, project_token, forkable):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uid=uid, project_token=project_token, name=name, status=2,
                                          forkable=forkable, peer_config=config, can_create=True)

    def confirm_workflow(self, uid, config, project_token, forkable):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uid=uid, project_token=project_token, status=5,
                                          forkable=forkable, peer_config=config, can_create=False)

    def fork_workflow(self, uid, name, project_token, config, peer_config):
        # TODO: implement 2pc (TCC) try() confirm() cancel()
        return self._grpc_update_workflow(uid=uid, name=name, project_token=project_token, status=5,
                                          config=peer_config, peer_config=config, can_create=True)
