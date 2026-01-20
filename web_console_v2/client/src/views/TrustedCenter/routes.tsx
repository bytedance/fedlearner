const INDEX_PATH = '/trusted-center';

const routes: Record<string, string> = {
  TrustedJobGroupList: `${INDEX_PATH}/list`,
  TrustedJobGroupDetail: `${INDEX_PATH}/detail/:id/:tabType(computing|export)`,
  TrustedJobGroupCreate: `${INDEX_PATH}/create/:role(receiver|sender)`,
  TrustedJobGroupEdit: `${INDEX_PATH}/edit/:id/:role(receiver|sender)`,
};

export default routes;
