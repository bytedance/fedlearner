import { useRecoilQuery } from 'hooks/recoil'
import React from 'react'
import { Redirect, Route, RouteProps } from 'react-router-dom'
import { userInfoGetters } from 'stores/user'

interface Props extends RouteProps {
  isAuthenticated?: boolean
}

function ProtectedRoute(props: Props) {
  const { isLoading, data } = useRecoilQuery(userInfoGetters)

  if (isLoading) {
    return <Route {...props} />
  }

  if (!data || !data.isAuthenticated) {
    return <Redirect to="/login" />
  }

  return <Route {...props} />
}

export default ProtectedRoute
