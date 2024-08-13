import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { typeInput } from 'shared/testUtils';
import InputGroup, { TColumn } from './index';
import i18n from 'i18n';

const columns: TColumn[] = [
  {
    type: 'TEXT',
    title: 'Role',
    dataIndex: 'role',
    span: 6,
    tooltip: '',
  },
  {
    type: 'INPUT_NUMBER',
    title: 'CPU',
    dataIndex: 'cpu',
    placeholder: '请输入',
    unitLabel: 'core',
    max: 100,
    precision: 1,
    span: 6,
    tooltip: i18n.t('tip_please_input_positive_integer'),
  },
  {
    type: 'INPUT_NUMBER',
    title: 'MEM',
    dataIndex: 'mem',
    unitLabel: 'GiB',
    span: 6,
    tooltip: i18n.t('tip_please_input_positive_integer'),
  },
  {
    type: 'INPUT_NUMBER',
    title: '实例数',
    dataIndex: 'instance',
    min: 1,
    max: 10,
    precision: 1,
    mode: 'button',
    span: 6,
    rules: [
      {
        max: 10,
        message: '太多拉！',
        validator(val: number, cb: any) {
          cb(val > 10 ? '太多拉' : undefined);
        },
      },
    ],
    tooltip: i18n.t('tip_replicas_range'),
  },
];

// confirm whether the value is right grid by grid
function checkLengthAndValue(inputList: HTMLElement[], valueList: any[], columns: TColumn[]) {
  const inputColumns = columns.filter((col) => col.type === 'INPUT' || col.type === 'INPUT_NUMBER');
  const totalLength = inputColumns.length * valueList.length;
  expect(inputList.length).toBe(totalLength);

  if (valueList.length === 0 || columns.length === 0) {
    return;
  }

  for (let i = 0; i < valueList.length; i++) {
    for (let j = 0; j < inputColumns.length; j++) {
      const { dataIndex, precision, type } = inputColumns[j] as any;
      const inputIndex = i * inputColumns.length + j;
      const val = valueList[i][dataIndex];
      switch (type) {
        case 'INPUT_NUMBER':
          expect(inputList[inputIndex]).toHaveValue(
            typeof val === 'number' ? val.toFixed(precision) : parseInt(val).toFixed(precision),
          );
          break;
        case 'INPUT':
          expect(inputList[inputIndex]).toHaveValue(val);
          break;
      }
    }
  }
}

describe('<InputGroup />', () => {
  it('initial with default value', () => {
    const defaultValue: any[] = [
      {
        role: 'worker',
        cpu: 1000,
        mem: '200',
        instance: 1,
      },
      {
        role: 'master',
        cpu: 1000,
        mem: '200',
        instance: 2,
      },
      {
        role: 'slave',
        cpu: 1000,
        mem: '200',
        instance: 30,
      },
    ];

    render(<InputGroup columns={columns} defaultValue={defaultValue} />);
    checkLengthAndValue(screen.queryAllByRole('textbox'), defaultValue, columns);
  });

  it('controlled mode', () => {
    const { rerender } = render(<InputGroup columns={columns} value={[]} />);
    // can't find any 'textbox' element
    expect(screen.queryAllByRole('gridcell').length).toBe(0);
    rerender(
      <InputGroup
        columns={columns}
        value={[
          {
            role: 'slave',
            cpu: 1000,
            mem: '200',
            instance: 30,
          },
        ]}
      />,
    );
    expect(screen.queryAllByRole('gridcell').length).toBe(1 * columns.length);
    rerender(
      <InputGroup
        columns={columns}
        value={[
          {
            role: 'slave',
            cpu: 1000,
            mem: '200',
            instance: 30,
          },
          {
            role: 'slave',
            cpu: 1000,
            mem: '200',
            instance: 30,
          },
        ]}
      />,
    );
    expect(screen.getAllByRole('gridcell').length).toBe(2 * columns.length);
  });

  it('only trigger onChange when all grid pass validation', async () => {
    const columns: TColumn[] = [
      {
        type: 'INPUT',
        dataIndex: 'name',
        title: 'test',
        span: 8,
        rules: [
          {
            validator(value, cb) {
              cb(/failed/i.test(value) ? 'name failed: ' + value : undefined);
            },
          },
        ],
      },
      {
        type: 'INPUT_NUMBER',
        dataIndex: 'sum',
        title: 'sum',
        span: 16,
        rules: [
          {
            validator(value, cb) {
              cb(value > 10 ? 'sum failed: ' + value : undefined);
            },
          },
        ],
      },
    ];
    const valueList = [
      { name: 'aaa', sum: 1 },
      { name: 'bbb', sum: 2 },
    ];
    const onChange = jest.fn();
    render(<InputGroup defaultValue={valueList} columns={columns} onChange={onChange} />);
    const inputList = screen.queryAllByRole('textbox');

    typeInput(inputList[0], 'failed');
    fireEvent.blur(inputList[0]);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledTimes(0);
    });

    typeInput(inputList[1], 100);
    fireEvent.blur(inputList[1]);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledTimes(0);
    });

    typeInput(inputList[0], 'success');
    fireEvent.blur(inputList[0]);
    typeInput(inputList[1], 1);
    fireEvent.blur(inputList[1]);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(expect.arrayContaining([{ name: 'success', sum: 1 }]));
    });
  });

  it('add button behavior', async () => {
    const columns: TColumn[] = [
      {
        title: 'name',
        dataIndex: 'name',
        type: 'INPUT',
        span: 12,
      },
      {
        title: 'sum',
        dataIndex: 'sum',
        type: 'INPUT_NUMBER',
        span: 12,
      },
    ];
    const onChange = jest.fn();
    render(<InputGroup columns={columns} onChange={onChange} />);
    checkLengthAndValue(screen.queryAllByRole('textbox'), [], columns);

    const addBtn = screen.getByTestId('addBtn');
    fireEvent.click(addBtn);
    checkLengthAndValue(screen.queryAllByRole('textbox'), [{ name: '', sum: 0 }], columns);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith([{ name: '', sum: 0 }]);
    });
  });

  it('remove button behavior', async () => {
    const columns: TColumn[] = [
      {
        title: 'name',
        dataIndex: 'name',
        type: 'INPUT',
        span: 12,
      },
      {
        title: 'sum',
        dataIndex: 'sum',
        type: 'INPUT_NUMBER',
        span: 12,
      },
    ];
    const valueList = [
      { name: 'a', sum: 1 },
      { name: 'b', sum: 2 },
      { name: 'c', sum: 3 },
    ];
    const onChange = jest.fn();
    render(<InputGroup columns={columns} defaultValue={[...valueList]} onChange={onChange} />);
    checkLengthAndValue(screen.queryAllByRole('textbox'), valueList, columns);

    const performDelete = async (rowIndex: number) => {
      const delBtnList = screen.queryAllByTestId('delBtn');
      valueList.splice(rowIndex, 1);
      fireEvent.click(delBtnList[rowIndex]);

      const inputList = screen.queryAllByRole('textbox');
      await waitFor(() => {
        checkLengthAndValue(inputList, valueList, columns);
        expect(onChange).toHaveBeenCalledWith(valueList);
      });
    };
    // test un-order deleting
    await performDelete(1);
    // after deleting one row , there're still two rows.
    await performDelete(1);
    // only one row left at this moment.
    await performDelete(0);
  });

  // the ui should not change when the value props remains unchanged.
  it('add/remove button behavior under controlled mode', async () => {
    const columns: TColumn[] = [
      {
        title: 'name',
        dataIndex: 'name',
        type: 'INPUT',
        span: 12,
      },
      {
        title: 'sum',
        dataIndex: 'sum',
        type: 'INPUT_NUMBER',
        span: 12,
      },
    ];
    const valueList = [
      { name: 'a', sum: 1 },
      { name: 'b', sum: 2 },
      { name: 'c', sum: 3 },
    ];
    const onChange = jest.fn();
    render(<InputGroup columns={columns} value={[...valueList]} onChange={onChange} />);
    const addBtn = screen.getByTestId('addBtn');
    fireEvent.click(addBtn);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(valueList.concat([{ name: '', sum: 0 }]));
    });
    expect(screen.getAllByRole('textbox').length).toBe(valueList.length * columns.length);

    const delBtnList = screen.getAllByTestId('delBtn');
    fireEvent.click(delBtnList[0]);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(valueList.slice(1));
    });
    expect(screen.getAllByRole('textbox').length).toBe(valueList.length * columns.length);
  });

  it('disableAddAndDelete should works', () => {
    const columns: TColumn[] = [
      {
        title: 'name',
        dataIndex: 'name',
        type: 'INPUT',
        span: 12,
      },
      {
        title: 'sum',
        dataIndex: 'sum',
        type: 'INPUT_NUMBER',
        span: 12,
      },
    ];
    const valueList = [
      { name: 'a', sum: 1 },
      { name: 'b', sum: 2 },
      { name: 'c', sum: 3 },
    ];

    render(<InputGroup columns={columns} defaultValue={valueList} disableAddAndDelete={true} />);
    expect(screen.queryByTestId('addBtn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('delBtn')).not.toBeInTheDocument();
  });

  it('formatValue should works', async () => {
    const onChange = jest.fn();
    const columns: TColumn[] = [
      {
        title: 'name',
        dataIndex: 'name',
        type: 'INPUT',
        span: 12,
        unitLabel: 'name',
        formatValue(val, col) {
          return val + col.unitLabel;
        },
      },
      {
        title: 'sum',
        dataIndex: 'sum',
        type: 'INPUT_NUMBER',
        span: 12,
        min: 1,
        unitLabel: 'sum',
        formatValue(value, col) {
          return value * 2;
        },
      },
    ];
    const valueList = [{ name: 'a', sum: '1' }];

    render(<InputGroup columns={columns} defaultValue={valueList} onChange={onChange} />);
    fireEvent.click(screen.getByTestId('addBtn'));
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(expect.arrayContaining([{ name: 'aname', sum: 2 }]));
    });
  });

  it('text with unitLabel should display correctly', () => {
    const columns: TColumn[] = [
      {
        title: '__name__',
        dataIndex: 'name',
        type: 'TEXT',
        span: 24,
        unitLabel: 'm',
      },
    ];
    const valueList = [{ name: '100m100m' }];
    render(<InputGroup columns={columns} defaultValue={valueList} />);
    expect(screen.getByText(/^100m100$/)).toBeInTheDocument();
    expect(screen.getByText(/^m$/)).toBeInTheDocument();
  });

  it('should render tooltip', async () => {
    const wrapper = render(<InputGroup columns={columns} value={[]} />);
    const $tooltipList = wrapper.getAllByTestId('tooltip-icon');
    expect($tooltipList.length).toBe(3);

    fireEvent.mouseOver($tooltipList[0]);

    await waitFor(() => {
      expect(screen.queryByText('tip_please_input_positive_integer')).toBeInTheDocument();
    });
  });
});
