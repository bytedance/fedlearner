import * as React from 'react';
import { Alert } from '@arco-design/web-react';

interface ErrorBoundaryProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
}

export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  {
    error?: Error | null;
    info: {
      componentStack?: string;
    };
  }
> {
  state = {
    error: undefined,
    info: {
      componentStack: '',
    },
  };

  componentDidCatch(error: Error | null, info: object) {
    this.setState({ error, info });
  }

  render() {
    const { title, description, children } = this.props;
    const {
      error,
      info: { componentStack },
    } = this.state;
    const errorTitle = typeof title === 'undefined' ? (error || '').toString() : title;
    const errorDescription = typeof description === 'undefined' ? componentStack : description;
    if (error) {
      return (
        <Alert
          type="error"
          style={{ overflow: 'auto' }}
          title={errorTitle}
          content={<pre>{errorDescription}</pre>}
        />
      );
    }
    return children;
  }
}
