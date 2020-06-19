import React, { useState } from 'react';
import { Loading, Popover, Text } from '@zeit-ui/react';

export default function PopConfirm({
  children, confirmText = 'Confirm',
  onConfirm = () => { }, onOk = () => { },
}) {
  const [loading, setLoading] = useState(false);
  const handleConfirm = async () => {
    setLoading(true);
    try {
      const res = await onConfirm();
      if (res.error) {
        throw new Error(res.error);
      }
      setLoading(false);
      onOk(res.data);
    } catch (err) {
      setLoading(false);
      // TODO: use setToast later
    }
  };
  return (
    <Popover
      content={(
        <div style={{ padding: '0 10px' }}>
          {loading
            ? <Loading type="error" />
            : (
              <Text
                type="success"
                style={{ margin: 0, cursor: 'pointer' }}
                onClick={handleConfirm}
              >{confirmText}</Text>
            )}
        </div>
      )}
    >
      {children}
    </Popover>
  );
}
