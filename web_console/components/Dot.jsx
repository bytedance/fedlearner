import React from 'react';

export default function Dot({ color = 'currentColor', size = '8px', style }) {
  return (
    <>
      <i className="dot" style={style} />
      <style jsx>{`
        .dot {
          display: inline-block;
          width: ${size};
          height: ${size};
          margin: calc(${size} / 2);
          border-radius: ${size};
          background: ${color};
          vertical-align: top;
        }
      `}</style>
    </>
  );
}
