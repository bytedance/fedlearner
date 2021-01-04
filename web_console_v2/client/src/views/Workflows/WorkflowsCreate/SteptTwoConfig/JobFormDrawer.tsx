import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
  ForwardRefRenderFunction,
} from 'react'
import styled from 'styled-components'
import { EyeOutlined, CloseOutlined } from '@ant-design/icons'
import { Drawer, Row, Button } from 'antd'
import { buildFormSchemaFromJob } from 'shared/formSchema'
import VariableSchemaForm, { formActions } from 'components/VariableSchemaForm'
import { FormilySchema } from 'typings/formily'
import GridRow from 'components/_base/GridRow'
import VariablePermission from 'components/VariblePermission'
import { useStoreActions, useStoreState } from 'react-flow-renderer'
import { DrawerProps } from 'antd/lib/drawer'
import {
  getNodeIdByJob,
  JobNodeData,
  JobNodeStatus,
} from 'components/WorlflowJobsFlowChart/helpers'
import { updateNodeStatusById } from 'components/WorlflowJobsFlowChart'
import { cloneDeep, omitBy } from 'lodash'
import { useRecoilState } from 'recoil'
import { workflowConfigValue } from 'stores/workflow'
import { IFormState } from '@formily/antd'
import { to } from 'shared/helpers'

const Container = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding-top: 0;
  }
`
const DrawerHeader = styled(Row)`
  height: 68px;
  margin: 0 -24px 0;
  padding-left: 24px;
  padding-right: 16px;
  border-bottom: 1px solid var(--darkGray9);
`
const DrawerTitle = styled.h3`
  margin-bottom: 0;
`
const PermissionDisplay = styled.div`
  margin: 0 -24px 42px;
  padding: 14px 24px;
  font-size: 12px;
  background-color: var(--gray1);
`
const FormContainer = styled.div`
  padding-right: 68px;
`
interface Props extends DrawerProps {
  data?: JobNodeData
  toggleVisible?: Function
  onConfirm: Function
}

export type JobFormDrawerExposedRef = {
  validateCurrentJobForm(): Promise<boolean>
  saveCurrentValues(): void
}

const JobFormDrawer: ForwardRefRenderFunction<JobFormDrawerExposedRef, Props> = (
  { data, toggleVisible, onConfirm, ...props },
  parentRef,
) => {
  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements)
  const [formSchema, setFormSchema] = useState<FormilySchema>(null as any)
  const jobNodes = useStoreState((store) => store.nodes)
  // Current config value from store
  const [configValues, setConfigValues] = useRecoilState(workflowConfigValue)
  useEffect(() => {
    if (data) {
      // NOTE: data.raw is unwritable by default from Recoil's design,
      // but meanwhile buildFormSchemaFromJob has side effects to data
      // so we need to make a copy here
      const jobData = cloneDeep(data)
      setFormSchema(buildFormSchemaFromJob(jobData.raw))
    }
  }, [data])
  useImperativeHandle(parentRef, () => {
    return {
      validateCurrentJobForm: validateCurrentForm,
      saveCurrentValues: saveCurrentValuesToRecoil,
    }
  })

  if (!data) {
    return null
  }

  const currentJobIdx = data.index
  const currentJobIdxDisplay = currentJobIdx + 1
  const isFinalStep = currentJobIdxDisplay === jobNodes.length
  const confirmButtonText = `${isFinalStep ? '配置完成' : '配置下一步（'} ${currentJobIdxDisplay}/${
    jobNodes.length
  }）`

  return (
    <Container
      getContainer="#app-content"
      title={data.raw.name}
      mask={false}
      width="640px"
      onClose={closeDrawer}
      headerStyle={{ display: 'none' }}
      {...props}
    >
      <DrawerHeader align="middle" justify="space-between">
        <DrawerTitle>上传数据集</DrawerTitle>
        <GridRow gap="10">
          <Button size="small" icon={<EyeOutlined />}>
            查看对方配置
          </Button>
          <Button size="small" icon={<CloseOutlined />} onClick={closeDrawer} />
        </GridRow>
      </DrawerHeader>

      <PermissionDisplay>
        <GridRow gap="20">
          <label>合作伙伴编辑权限:</label>
          <VariablePermission.Writable desc />
          <VariablePermission.Readable desc />
          <VariablePermission.Private desc />
        </GridRow>
      </PermissionDisplay>

      {/* ☢️ Form Area */}
      <FormContainer>
        {formSchema && (
          <VariableSchemaForm
            schema={formSchema}
            onConfirm={confirmAndGoNextJob}
            onCancel={closeDrawer}
            confirmText={confirmButtonText}
            cancelText={'关闭'}
          />
        )}
      </FormContainer>
    </Container>
  )

  function deselectAllNode() {
    setSelectedElements([])
  }
  async function validateCurrentForm(): Promise<boolean> {
    // When no Node opened yet
    if (!data) return true

    const nodeId = getNodeIdByJob(data.raw)
    const { Unfinished, Completed } = JobNodeStatus
    const [_, error] = await to(formActions.validate())

    updateNodeStatusById({
      id: nodeId,
      status: error ? Unfinished : Completed,
    })

    return !error
  }
  function closeDrawer() {
    saveCurrentValuesToRecoil()
    // validate current form and tag corresponding Node status
    validateCurrentForm()
    toggleVisible && toggleVisible(false)
    deselectAllNode()
  }
  async function confirmAndGoNextJob() {
    if (isFinalStep) {
      return closeDrawer()
    }
    const valid = await validateCurrentForm()
    saveCurrentValuesToRecoil()

    if (!valid) return
    const nextNodeToSelect = jobNodes.find((node) => node.data.index === currentJobIdx + 1)

    if (nextNodeToSelect) {
      setSelectedElements([nextNodeToSelect])
      onConfirm && onConfirm(nextNodeToSelect)
    }
  }
  function saveCurrentValuesToRecoil() {
    formActions.getFormState((state: IFormState) => {
      const { jobs, group_alias } = configValues

      const jobsValuesCopy = cloneDeep(jobs)

      jobsValuesCopy[currentJobIdx] = omitBy(state.values, (v: any) => v === undefined)

      setConfigValues({
        group_alias,
        jobs: jobsValuesCopy,
      })
    })
  }
}

export default forwardRef(JobFormDrawer)
