import { Menu } from 'antd';
import styled from 'styled-components';

const PrettyMenu = styled(Menu)`
  width: 250px;
  min-height: 50px;
  max-height: 500px;
  padding: 8px 5px;
  background-color: rgba(237, 238, 238, 0.76);
  border-radius: 5px;
  overflow-x: hidden;
  overflow-y: auto;
  backdrop-filter: blur(3px);
`;

export const PrettyMenuItem = styled(Menu.Item)`
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 38px;
  padding: 0 13px;
  border-radius: 5px;

  &:hover {
    background-color: rgba(255, 255, 255, 0.8);
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  }
`;

export default PrettyMenu;
