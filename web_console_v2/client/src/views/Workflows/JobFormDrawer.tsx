import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
  ForwardRefRenderFunction,
} from 'react';
import styled from './JobFormDrawer.module.less';
import { Drawer, DrawerProps, Grid, Button } from '@arco-design/web-react';
import buildFormSchemaFromJobDef from 'shared/formSchema';
import { FormilySchema } from 'typings/formily';
import GridRow from 'components/_base/GridRow';
import VariablePermission from 'components/VariblePermission';
import { JobNodeRawData, GlobalNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { cloneDeep, noop } from 'lodash-es';
import { giveWeakRandomKey } from 'shared/helpers';
import { useTranslation } from 'react-i18next';
import { IconClose, IconEye } from '@arco-design/web-react/icon';
import ErrorBoundary from 'components/ErrorBoundary';
import { Variable, VariableComponent } from 'typings/variable';

const Row = Grid.Row;

interface Props extends DrawerProps {
  message?: string;
  readonly?: boolean;
  isPeerSide?: boolean;
  currentIdx?: number;
  nodesCount: number;
  jobDefinition?: JobNodeRawData | GlobalNodeRawData;
  initialValues?: Variable[];
  toggleVisible?: Function;
  onGoNextJob: Function;
  onCloseDrawer: Function;
  onViewPeerConfigClick?: (...args: any[]) => void;
  showPeerConfigButton?: boolean;
}
export type JobFormDrawerExposedRef = {
  validateCurrentForm(): Promise<boolean>;
  getFormValues(): Promise<Record<string, any>>;
};

const JobFormDrawer: ForwardRefRenderFunction<JobFormDrawerExposedRef, Props> = (
  {
    isPeerSide,
    currentIdx,
    nodesCount,
    jobDefinition,
    initialValues,
    toggleVisible,
    readonly,
    message,
    onGoNextJob,
    showPeerConfigButton,
    onViewPeerConfigClick,
    onCloseDrawer,

    ...props
  },
  parentRef,
) => {
  const { t } = useTranslation();
  const [, setRandomKey] = useState<string>(giveWeakRandomKey());
  const [, setFormSchema] = useState<FormilySchema>(null as any);

  useEffect(() => {
    if (jobDefinition) {
      // Force to re-render schema form to prevent it remember previous values
      setRandomKey(giveWeakRandomKey());

      // hide FeatureSelect component
      const normalizedJobDefinition = {
        ...jobDefinition,
        variables: (jobDefinition.variables || []).filter((item) => {
          if (item?.widget_schema?.component === VariableComponent.FeatureSelect) {
            return false;
          }
          return true;
        }),
      };

      // prop 'node' is from `templateInUsing` which only has job definition
      // in order to hydrate the Form, we need get user-inputs (whick stored on `workflowConfigForm`)
      // and merge the user-inputs to definition
      const jobDefWithValues = _hydrate(normalizedJobDefinition, initialValues);
      const schema = buildFormSchemaFromJobDef(jobDefWithValues, {
        withPermissions: isPeerSide,
        readonly,
      });
      setFormSchema(schema);
    }
  }, [jobDefinition, initialValues, isPeerSide, readonly]);

  useImperativeHandle(parentRef, () => {
    return {
      validateCurrentForm: validateCurrentForm,
      getFormValues,
    };
  });

  if (!jobDefinition) {
    return null;
  }

  return (
    <ErrorBoundary>
      <Drawer
        className={styled.container}
        {...props}
        mask={false}
        width="640px"
        headerStyle={{ display: 'none' }}
        onCancel={closeDrawer}
        closable={false}
        wrapClassName="#app-content"
        footer={null}
      >
        <Row className={styled.drawer_header} align="center" justify="space-between">
          <h3 className={styled.drawer_title}>{jobDefinition.name}</h3>
          <GridRow gap="10">
            {showPeerConfigButton && (
              <Button size="small" icon={<IconEye />} onClick={onViewPeerConfigClick || noop}>
                {t('workflow.btn_see_peer_config')}
              </Button>
            )}
            <Button size="small" icon={<IconClose />} onClick={closeDrawer} />
          </GridRow>
        </Row>

        {message && <small className={styled.message}>{message}</small>}

        <div className={styled.permission_display}>
          <GridRow gap="20">
            <label>{t('workflow.ptcpt_permission')}:</label>
            <VariablePermission.Writable desc />
            <VariablePermission.Readable desc />
            <VariablePermission.Private desc />
          </GridRow>
        </div>
      </Drawer>
    </ErrorBoundary>
  );

  async function validateCurrentForm(): Promise<boolean> {
    // When no Node opened yet
    if (!jobDefinition) return true;

    // const [, error] = await to(form.validate());

    return false;
  }
  function closeDrawer() {
    // validate current form and mark Node with corresponding status
    validateCurrentForm();
    toggleVisible && toggleVisible(false);
    onCloseDrawer();
  }

  function getFormValues(): Promise<Record<string, any>> {
    return new Promise((resolve) => {
      resolve({});
    });
  }
};

function _hydrate(jobDefinition: JobNodeRawData | GlobalNodeRawData, varsWithValue?: Variable[]) {
  if (!varsWithValue) return jobDefinition;

  const jobDefCopy = cloneDeep(jobDefinition);

  jobDefCopy.variables.forEach((def) => {
    const value = varsWithValue.find((item) => item.name === def.name)?.value;

    if (value) {
      def.value = value;
    }
  });

  return jobDefCopy;
}

export default forwardRef(JobFormDrawer);
