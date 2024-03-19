import React, { FC } from 'react';
import styled from 'styled-components';
import { isOperable, isForkable, isEditable } from 'shared/workflow';
import { Workflow, WorkflowState } from 'typings/workflow';
import { useTranslation } from 'react-i18next';
import { Button, Message, Spin, Popconfirm } from '@arco-design/web-react';
import { useHistory } from 'react-router-dom';
import {
  getPeerWorkflowsConfig,
  runTheWorkflow,
  stopTheWorkflow,
  invalidTheWorkflow,
  getWorkflowDetailById,
} from 'services/workflow';
import WorkflowAccessControl from './WorkflowAccessControl';
import GridRow from 'components/_base/GridRow';
import {
  IconCopy,
  IconSync,
  IconTool,
  IconPlayCircle,
  IconPause,
  IconEdit,
  IconMindMapping,
} from '@arco-design/web-react/icon';
import { useToggle } from 'react-use';
import { to } from 'shared/helpers';
import ErrorBoundary from 'components/ErrorBoundary';
import MoreActions, { ActionItem } from 'components/MoreActions';
import Modal from 'components/Modal';

const Container = styled(GridRow)`
  width: fit-content;
  margin-left: ${(props: any) => (props.type === 'link' ? '-10px !important' : 0)};
`;
const Link = styled.span`
  color: var(--primaryColor);
  cursor: pointer;
  margin-left: 8px;
`;

type Action = 'edit' | 'configure' | 'run' | 'rerun' | 'stop' | 'fork' | 'invalid' | 'accessCtrl';

type Props = {
  workflow: Workflow;
  type?: 'text' | 'default';
  size?: 'small' | 'mini';
  isShowMoreAction?: boolean;
  without?: Action[];
  showIcon?: boolean;
  onSuccess?: Function;
  onEditClick?: Function;
  onAcceptClick?: Function;
  onForkClick?: Function;
};

const icons: Partial<Record<Action, any>> = {
  configure: IconTool,
  run: IconPlayCircle,
  rerun: IconSync,
  stop: IconPause,
  fork: IconCopy,
  edit: IconEdit,
  accessCtrl: IconMindMapping,
};

const WorkflowActions: FC<Props> = ({
  workflow,
  type = 'default',
  isShowMoreAction = false,
  without = [],
  onSuccess,
  size,
  ...restProps
}) => {
  const { t } = useTranslation();
  const history = useHistory();
  const [loading, toggleLoading] = useToggle(false);
  const {
    RUNNING,
    STOPPED,
    INVALID,
    COMPLETED,
    FAILED,
    PENDING_ACCEPT,
    READY_TO_RUN,
    PARTICIPANT_CONFIGURING,
  } = WorkflowState;

  const { state } = workflow;

  const visible: Partial<Record<Action, boolean>> = {
    configure: state === PENDING_ACCEPT && !without?.includes('configure'),
    run: (state === READY_TO_RUN || state === PARTICIPANT_CONFIGURING) && !without?.includes('run'),
    stop: state === RUNNING && !without?.includes('stop'),
    rerun:
      (state === STOPPED || state === COMPLETED || state === FAILED) && !without?.includes('rerun'),
    fork: !without?.includes('fork'),
    accessCtrl: !without?.includes('accessCtrl'),
    invalid: !without?.includes('fork') && !(state === INVALID),
    edit: !without?.includes('edit'),
  };

  const isDisabled = !isOperable(workflow);

  const disabled = {
    configure: false,
    run: isDisabled,
    stop: isDisabled,
    rerun: isDisabled,
    fork: !isForkable(workflow),
    invalid: false,
    accessCtrl: false,
    edit: !isEditable(workflow),
  };

  const isDefaultType = type === 'default';

  let actionList: ActionItem[] = [];

  if (isShowMoreAction) {
    actionList = [
      {
        label: t('workflow.action_fork'),
        disabled: !visible.fork || disabled.fork,
        onClick: onForkClick,
      },
      {
        label: t('workflow.action_invalid'),
        disabled: !visible.invalid || disabled.invalid,
        onClick: () => {
          Modal.confirm({
            title: t('workflow.msg_sure_to_invalidate_title'),
            content: t('workflow.msg_sure_to_invalidate_content'),
            onOk() {
              onInvalidClick();
            },
          });
        },
        danger: true,
      },
    ];
  }

  return (
    <ErrorBoundary>
      <Spin loading={loading} style={{ width: 'fit-content' }}>
        <Container {...{ type }} gap={isDefaultType ? 8 : 0}>
          {visible.edit && (
            <Button
              size={size || 'small'}
              type={type}
              icon={withIcon('edit')}
              disabled={disabled.edit}
              onClick={onEditClick}
            >
              {t('workflow.action_edit')}
            </Button>
          )}
          {visible.configure && (
            <Button
              size={size || 'small'}
              type={type}
              icon={withIcon('configure')}
              onClick={onAcceptClick}
            >
              {t('workflow.action_configure')}
            </Button>
          )}
          {visible.run && (
            <Button
              size={size || 'small'}
              type={type}
              icon={withIcon('run')}
              onClick={onRunClick}
              disabled={disabled.run}
            >
              {t('workflow.action_run')}
            </Button>
          )}
          {visible.stop && (
            <Popconfirm
              title={t('workflow.msg_sure_to_stop')}
              onConfirm={onStopClick}
              disabled={disabled.stop}
              okText="确 定"
              cancelText="取 消"
            >
              <Button
                size={size || 'small'}
                type={type}
                icon={withIcon('stop')}
                disabled={disabled.stop}
              >
                {t('workflow.action_stop_running')}
              </Button>
            </Popconfirm>
          )}
          {visible.rerun && (
            <Button
              size={size || 'small'}
              type={type}
              icon={withIcon('rerun')}
              onClick={onRunClick}
              disabled={disabled.rerun}
            >
              {t('workflow.action_re_run')}
            </Button>
          )}
          {!isShowMoreAction && visible.fork && (
            <Button
              size={size || 'small'}
              type={type}
              icon={withIcon('fork')}
              onClick={onForkClick}
              disabled={disabled.fork}
            >
              {t('workflow.action_fork')}
            </Button>
          )}
          {!isShowMoreAction && visible.invalid && (
            <Popconfirm
              title={t('workflow.msg_sure_to_invalidate_title')}
              onConfirm={onInvalidClick}
              okText="确 定"
              cancelText="取 消"
            >
              <Button
                size={size || 'small'}
                type={type}
                status="danger"
                disabled={disabled.invalid}
              >
                {t('workflow.action_invalid')}
              </Button>
            </Popconfirm>
          )}
          {visible.accessCtrl && (
            <WorkflowAccessControl
              icon={withIcon('accessCtrl')}
              size={size || 'small'}
              type={type}
              workflow={workflow}
              disabled={disabled.accessCtrl}
              onSuccess={onWorkflowAccessControlSuccess}
            />
          )}
          {isShowMoreAction && <MoreActions actionList={actionList} />}
        </Container>
      </Spin>
    </ErrorBoundary>
  );

  function withIcon(action: Action) {
    if (!isDefaultType) return undefined;

    const Ico = icons[action];

    if (!Ico) return undefined;

    return <Ico />;
  }
  function onEditClick() {
    if (restProps.onEditClick) {
      restProps.onEditClick();
      return;
    }
    history.push(`/workflow-center/workflows/edit/basic/${workflow.id}`);
  }
  function onAcceptClick() {
    if (restProps.onAcceptClick) {
      restProps.onAcceptClick();
      return;
    }
    history.push(`/workflow-center/workflows/accept/basic/${workflow.id}`);
  }
  async function onForkClick() {
    if (restProps.onForkClick) {
      restProps.onForkClick();
      return;
    }

    try {
      // Get is_local field by workflow detail api
      toggleLoading(true);
      const workflowDetail = await getWorkflowDetailById(workflow.id);

      const isLocal = workflowDetail.data.is_local;

      if (!isLocal) {
        const [res, error] = await to(getPeerWorkflowsConfig(workflow.id));
        toggleLoading(false);

        if (error) {
          return Message.error(t('workflow.msg_get_peer_cfg_failed') + error.message);
        }

        const anyPeerWorkflow = Object.values(res.data).find((item) => !!item.uuid)!;
        if (!anyPeerWorkflow.forkable) {
          Message.warning(t('workflow.msg_unforkable'));
          return;
        }
      }

      history.push(`/workflow-center/workflows/fork/basic/${workflow.id}`);
    } catch (error) {
      toggleLoading(false);
      Message.error(error.message);
    }
  }
  async function onRunClick() {
    toggleLoading(true);
    try {
      await runTheWorkflow(workflow.id, workflow.project_id);
      onSuccess?.(workflow);
    } catch (error) {
      // Hard code tip when project.variables is missing
      // i.e. error.message = Invalid Variable when try to format the job u8e63b65b8ee941c8b94-raw:Unknown placeholder: project.variables.xyx-test
      if (error.message) {
        const regx = /project\.variables\.([^\s]*)/;
        const result = String(error.message).match(regx);
        if (result && result[1]) {
          Message.warning({
            content: (
              <>
                <span>
                  {t('workflow.msg_project_variables_required', {
                    var: result[1],
                  })}
                </span>
                <Link
                  onClick={(e) => {
                    history.push(`/projects/edit/${workflow.project_id}`);
                  }}
                >
                  {t('workflow.msg_project_variables_link')}
                </Link>
              </>
            ),
          });
        } else {
          Message.error(error.message);
        }
      }
    }
    toggleLoading(false);
  }
  async function onStopClick() {
    toggleLoading(true);
    try {
      await stopTheWorkflow(workflow.id, workflow.project_id);
      onSuccess?.(workflow);
    } catch (error) {
      Message.error(error.message);
    }
    toggleLoading(false);
  }
  async function onInvalidClick() {
    toggleLoading(true);
    try {
      await invalidTheWorkflow(workflow.id, workflow.project_id);
      onSuccess?.(workflow);
    } catch (error) {
      Message.error(error.message);
    }
    toggleLoading(false);
  }

  function onWorkflowAccessControlSuccess() {
    onSuccess?.(workflow);
  }
};

export default WorkflowActions;
