import React from 'react';
import { render, act } from '@testing-library/react';
import CountTime from './index';

describe('<CountTime />', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  describe('count down', () => {
    it('should render correctly and trigger onCountDownFinish one time when countdown to zero', () => {
      const onCountDownFinish = jest.fn();
      const wrapper = render(
        <CountTime time={10} isCountDown={true} onCountDownFinish={onCountDownFinish} />,
      );
      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(wrapper.queryByText('00:00:09')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(999);
      });
      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1);
      });
      expect(wrapper.queryByText('00:00:07')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(7000);
      });
      expect(wrapper.queryByText('00:00:00')).toBeInTheDocument();
      expect(onCountDownFinish).toHaveBeenCalledTimes(1);

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('00:00:00')).toBeInTheDocument();
      expect(onCountDownFinish).toHaveBeenCalledTimes(1);
    });

    it('should only render second', () => {
      const onCountDownFinish = jest.fn();
      const wrapper = render(
        <CountTime
          time={70}
          isCountDown={true}
          onCountDownFinish={onCountDownFinish}
          isOnlyShowSecond={true}
        />,
      );
      expect(wrapper.queryByText('70')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(wrapper.queryByText('69')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('68')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(999);
      });
      expect(wrapper.queryByText('68')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1);
      });
      expect(wrapper.queryByText('67')).toBeInTheDocument();
      expect(onCountDownFinish).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(7000);
      });
      expect(wrapper.queryByText('60')).toBeInTheDocument();
      expect(onCountDownFinish).toHaveBeenCalledTimes(0);

      act(() => {
        jest.advanceTimersByTime(60000);
      });
      expect(wrapper.queryByText('0')).toBeInTheDocument();
      expect(onCountDownFinish).toHaveBeenCalledTimes(1);

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('0')).toBeInTheDocument();
      expect(onCountDownFinish).toHaveBeenCalledTimes(1);
    });
  });

  describe('count up', () => {
    it('should render correctly', () => {
      const wrapper = render(<CountTime time={10} isCountDown={false} />);
      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('00:00:11')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('00:00:12')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(999);
      });
      expect(wrapper.queryByText('00:00:12')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1);
      });
      expect(wrapper.queryByText('00:00:13')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(7000);
      });

      expect(wrapper.queryByText('00:00:20')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(41000);
      });

      expect(wrapper.queryByText('00:01:01')).toBeInTheDocument();
    });

    it('should only render second', () => {
      const wrapper = render(<CountTime time={70} isCountDown={false} isOnlyShowSecond={true} />);
      expect(wrapper.queryByText('70')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(wrapper.queryByText('71')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(wrapper.queryByText('72')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(999);
      });
      expect(wrapper.queryByText('72')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(1);
      });
      expect(wrapper.queryByText('73')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(7000);
      });
      expect(wrapper.queryByText('80')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(60000);
      });
      expect(wrapper.queryByText('140')).toBeInTheDocument();
    });
  });

  it('should render static time', () => {
    const wrapper = render(<CountTime time={10} isCountDown={true} isStatic={true} />);
    expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(2000);
    });

    expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();
  });

  describe('change isStatic prop', () => {
    it('should reset time on change isStatic prop', () => {
      const wrapper = render(
        <CountTime time={10} isCountDown={true} isStatic={false} isResetOnChange={true} />,
      );
      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();

      wrapper.rerender(
        <CountTime time={10} isCountDown={true} isStatic={true} isResetOnChange={true} />,
      );
      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();
    });

    it('should not reset time on change prop', () => {
      const wrapper = render(
        <CountTime time={10} isCountDown={true} isStatic={false} isResetOnChange={false} />,
      );
      expect(wrapper.queryByText('00:00:10')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();

      wrapper.rerender(
        <CountTime time={10} isCountDown={true} isStatic={true} isResetOnChange={false} />,
      );
      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();

      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(wrapper.queryByText('00:00:08')).toBeInTheDocument();
    });
  });

  it('should support render props mode', () => {
    const onCountDownFinish = jest.fn();

    const wrapper = render(
      <CountTime
        time={10}
        isCountDown={true}
        isRenderPropsMode={true}
        onCountDownFinish={onCountDownFinish}
      >
        {(formattedTime: string, noFormattedTime: number) => {
          return (
            <>
              <div>formattedTime: {formattedTime}</div>
              <div>noFormattedTime: {noFormattedTime}</div>
            </>
          );
        }}
      </CountTime>,
    );

    expect(wrapper.queryByText('formattedTime: 00:00:10')).toBeInTheDocument();
    expect(wrapper.queryByText('noFormattedTime: 10')).toBeInTheDocument();
    expect(onCountDownFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(wrapper.queryByText('formattedTime: 00:00:05')).toBeInTheDocument();
    expect(wrapper.queryByText('noFormattedTime: 5')).toBeInTheDocument();
    expect(onCountDownFinish).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(wrapper.queryByText('formattedTime: 00:00:00')).toBeInTheDocument();
    expect(wrapper.queryByText('noFormattedTime: 0')).toBeInTheDocument();
    expect(onCountDownFinish).toHaveBeenCalledTimes(1);

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(wrapper.queryByText('formattedTime: 00:00:00')).toBeInTheDocument();
    expect(wrapper.queryByText('noFormattedTime: 0')).toBeInTheDocument();
    expect(onCountDownFinish).toHaveBeenCalledTimes(1);
  });
});
