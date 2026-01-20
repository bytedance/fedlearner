import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { sleep, getRandomInt } from 'shared/helpers';
import Component from './index';

describe('<BlockRadio />', () => {
  test('default props layout', () => {
    const options = Array(3)
      .fill(0)
      .map((_, index) => {
        return {
          value: index,
          label: `option ${index}`,
        };
      });
    const props = {
      options,
      isCenter: true,
      gap: 77,
    };
    const { container } = render(<Component {...props} />);
    expect(container.firstChild).toMatchSnapshot();
  });

  test('beforeChange and onChange should be called', async () => {
    const beforeChange = jest.fn();
    const onChange = jest.fn();
    const optionsLength = getRandomInt(10, 20);

    const props = {
      options: generateRandomOptions(optionsLength),
      beforeChange,
      onChange,
    };

    render(<Component {...props} />);
    const blockList = screen.getAllByRole('radio');
    const randomNumGenerator = getRandomIntWrapper(0, optionsLength - 1);
    let clickIndex: number;

    // --------------
    beforeChange.mockReturnValue(Promise.resolve(false));
    clickIndex = randomNumGenerator.next();
    fireEvent.click(blockList[clickIndex]);
    expect(beforeChange).toHaveBeenCalledWith(clickIndex);
    expect(beforeChange).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledTimes(0);
    });

    // --------------
    beforeChange.mockReturnValue(Promise.resolve(true));
    clickIndex = randomNumGenerator.next();

    fireEvent.click(blockList[clickIndex]);
    // beforeChange 之前已经执行过一次，所以是 2
    expect(beforeChange).toHaveBeenCalledWith(clickIndex);
    expect(beforeChange).toHaveBeenCalledTimes(2);
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(clickIndex);
      expect(onChange).toHaveBeenCalledTimes(1);
    });

    // --------------
    beforeChange.mockReturnValue(sleep(1000).then(() => true));
    clickIndex = randomNumGenerator.next();
    fireEvent.click(blockList[clickIndex]);
    expect(beforeChange).toHaveBeenCalledWith(clickIndex);
    expect(beforeChange).toHaveBeenCalledTimes(3);
    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith(clickIndex);
        expect(onChange).toHaveBeenCalledTimes(2);
      },
      { timeout: 2000 },
    );
  });

  test('renderBlockInner should work', async () => {
    const optionsLength = getRandomInt(10, 20);
    const renderBlockInner = jest.fn((props, options) => {
      return <h1 className={options.isActive ? 'active' : ''}>{props.value}</h1>;
    });
    const props = {
      options: generateRandomOptions(optionsLength),
      renderBlockInner,
    };

    const { rerender } = render(<Component {...props} />);
    expect(renderBlockInner).toHaveBeenCalledTimes(optionsLength);
    expect(renderBlockInner).toHaveBeenCalledWith(
      expect.objectContaining({
        label: expect.any(String),
        value: expect.any(Number),
      }),
      expect.objectContaining({
        label: expect.anything(),
        isActive: expect.any(Boolean),
      }),
    );

    // 如果 value 改变，应该在相应下标传入 isActive
    const selectedIndex = getRandomInt(0, optionsLength - 1);
    rerender(<Component {...props} value={selectedIndex} />);
    const blockList = screen.getAllByRole('radio');
    const activeBlock = blockList[selectedIndex];
    const innerContent = activeBlock.querySelector('.active');
    await waitFor(() => {
      expect(innerContent).toBeTruthy();
    });
  });

  test('set option to disabled should work', async () => {
    const optionsLength = getRandomInt(10, 20);
    const disabledIndex = getRandomInt(0, optionsLength - 1);
    const options = generateRandomOptions(optionsLength);
    const onChange = jest.fn();

    options[disabledIndex].disabled = true;
    const props = {
      options,
      onChange,
    };

    render(<Component {...props} />);

    const blockList = screen.getAllByRole('radio');
    const disabledBlock = blockList[disabledIndex];
    fireEvent.click(disabledBlock);

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledTimes(0);
    });
  });
});

function generateRandomOptions(length = 4) {
  return Array(length)
    .fill(0)
    .map((_, index) => {
      return {
        value: index,
        label: `option ${index}`,
        disabled: false,
      };
    });
}

function getRandomIntWrapper(min = 1, max = 10) {
  const record: number[] = [];

  return {
    next() {
      if (record.length >= max - min) {
        throw new Error('record overflow');
      }

      let tmp = getRandomInt(min, max);
      while (record.includes(tmp) === true) {
        tmp = getRandomInt(min, max);
      }
      record.push(tmp);
      return tmp;
    },
  };
}
