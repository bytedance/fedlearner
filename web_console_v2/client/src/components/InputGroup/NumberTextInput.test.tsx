import React, { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import NumberInputNumber, { CpuInput, MemInput } from './NumberTextInput';

function typeInput(input: HTMLElement, value: string | number) {
  fireEvent.change(input, {
    target: { value },
  });
}

function triggerValueChange(input: HTMLElement, value: string | number) {
  typeInput(input, value);
  fireEvent.blur(input);
}

// partly borrow from arco design repo
describe('<NumberTextInput />', () => {
  it('init value correctly', () => {
    const defaultValue = 8;
    render(<NumberInputNumber defaultValue={defaultValue} min={0} max={12} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue(defaultValue.toString());
    typeInput(input, 1000);
    expect(input).toHaveValue('1000');
    fireEvent.blur(input);
    expect(input).toHaveValue('12');

    typeInput(input, -1000);
    expect(input).toHaveValue('-1000');
    fireEvent.blur(input);
    expect(input).toHaveValue('0');
  });

  it('init value with empty string correctly', () => {
    render(<NumberInputNumber value="" />);
    expect(screen.getByRole('textbox')).toHaveValue('');
  });

  it('init value with string correctly', () => {
    render(<NumberInputNumber value="8.0000" precision={2} />);
    expect(screen.getByRole('textbox')).toHaveValue('8.00');
  });

  it('value control mode', () => {
    const Demo = () => {
      const [value, setValue] = useState<number | undefined>(0);
      return (
        <div>
          <button id="clear" onClick={() => setValue(undefined)}>
            clear
          </button>
          <NumberInputNumber value={value} min={10} />;
        </div>
      );
    };
    render(<Demo />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('0');
    fireEvent.click(screen.getByRole('button'));
    expect(input).toHaveValue('');
  });

  it('typing input', () => {
    render(<NumberInputNumber min={0} max={100} />);
    const input = screen.getByRole('textbox');
    triggerValueChange(input, 'abcdefg');
    expect(input).toHaveValue('');

    triggerValueChange(input, '100abcdefg');
    expect(input).toHaveValue('100');

    triggerValueChange(input, '1.0000abcdef');
    expect(input).toHaveValue('1');

    triggerValueChange(input, '1000');
    // because the max is 100
    expect(input).toHaveValue('100');

    triggerValueChange(input, '-100');
    // because the min is 0
    expect(input).toHaveValue('0');
  });

  it('onChange calling', () => {
    const onChange = jest.fn();
    render(<NumberInputNumber onChange={onChange} />);
    const input = screen.getByRole('textbox');

    typeInput(input, '1000');
    expect(onChange).toHaveBeenCalledTimes(0);
    fireEvent.blur(input);
    expect(onChange).toHaveBeenCalledWith(1000);
    expect(onChange).toHaveBeenCalledTimes(1);

    // should ignore empty string
    typeInput(input, '');
    expect(onChange).toHaveBeenCalledTimes(1);
    fireEvent.blur(input);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('onChange calling with correct approximate value', () => {
    const onChange = jest.fn();
    const { rerender } = render(<NumberInputNumber defaultValue={8.5} precision={0} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('9');

    rerender(<NumberInputNumber onChange={onChange} precision={2} />);
    triggerValueChange(input, '8.666');
    expect(onChange).toHaveBeenCalledWith(8.67);
  });
});

describe('CpuInput', () => {
  it('should render correctly', () => {
    const wrapper = render(<CpuInput />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Core');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('');
  });
  it('should render correctly with value', () => {
    const wrapper = render(<CpuInput value="1500m" />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Core');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('1.5');
  });

  it('onChange calling with unit value', () => {
    const onChange = jest.fn();
    const wrapper = render(<CpuInput value="1500m" onChange={onChange} />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Core');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('1.5');

    triggerValueChange($input, '3');
    expect(onChange).toHaveBeenCalledWith('3000m');
  });
});

describe('MemInput', () => {
  it('should render correctly', () => {
    const wrapper = render(<MemInput />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Gi');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('');
  });
  it('should render correctly with value', () => {
    const wrapper = render(<MemInput value="3Gi" />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Gi');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('3');
  });

  it('onChange calling with unit value', () => {
    const onChange = jest.fn();
    const wrapper = render(<MemInput value="3Gi" onChange={onChange} />);
    const $input = wrapper.getByRole('textbox') as HTMLInputElement;
    const $unit = wrapper.getByText('Gi');
    expect($input).toBeInTheDocument();
    expect($unit).toBeInTheDocument();
    expect($input.value).toBe('3');

    triggerValueChange($input, '64');
    expect(onChange).toHaveBeenCalledWith('64Gi');
  });
});
