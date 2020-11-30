import React from 'react'
import routes from './routes'

import { Switch, Route } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'

function RouterViews() {
  return (
    <Switch>
      {routes.map((route, index) => {
        const RouteComponent = route.auth ? ProtectedRoute : Route

        return (
          <RouteComponent
            key={index}
            path={route.path}
            exact={route.exact}
            render={(props: any) => <route.component {...props} routes={route.children} />}
          />
        )
      })}
    </Switch>
  )
}

export default RouterViews
