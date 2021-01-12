import { Spin } from 'antd'
import { useRecoilQuery } from 'hooks/recoil'
import React, { FC } from 'react'
import { projectListQuery } from 'stores/projects'

const ProjectCell: FC<{ id: number }> = ({ id }) => {
  const { isLoading, data } = useRecoilQuery(projectListQuery)

  if (isLoading) {
    return <Spin size="small" />
  }

  const project = data?.find((pj) => pj.id === id) || { name: 'none' }

  return <div>{project.name}</div>
}

export default ProjectCell
