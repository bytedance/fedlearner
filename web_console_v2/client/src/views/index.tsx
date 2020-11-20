import React from 'react'
import routes from './routes'

import { Switch, Route } from 'react-router-dom'

function RouterViews() {
  return (
    <Switch>
      {routes.map((route, index) => (
        <Route
          key={index}
          path={route.path}
          exact={route.exact}
          render={(props) => <route.component {...props} routes={route.children} />}
        />
      ))}
      <Route path="*">You are lost</Route>
    </Switch>
  )
}

export default RouterViews
