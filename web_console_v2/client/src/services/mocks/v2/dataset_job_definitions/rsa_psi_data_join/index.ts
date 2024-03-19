import { DataJobVariable } from 'typings/dataset';
import {
  stringInput,
  numberInput,
  objectInput,
  listInput,
  asyncSwitch,
  codeEditor,
  hideStringInput,
} from '../../variables/examples';

const get = {
  data: {
    data: {
      is_federated: false,
      variables: [
        hideStringInput,
        stringInput,
        numberInput,
        asyncSwitch,
        objectInput,
        listInput,
        codeEditor,
      ].map((item) => {
        return {
          ...item,
          widget_schema: JSON.stringify(item.widget_schema),
        };
      }) as DataJobVariable[],
    },
  },
  status: 200,
};

export default get;
