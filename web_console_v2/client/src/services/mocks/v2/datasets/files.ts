import { FileToImport } from 'typings/dataset';

const get = {
  data: {
    data: [
      {
        source_path: '/root/admin/rw_datas/f_1.db',
        size: 123456,
        created_at: 1601937685,
      },
      {
        source_path: '/root/admin/rw_datas/f_2.db',
        size: 445678,
        created_at: 1678937685,
      },
      {
        source_path: '/root/admin/fl_datas/f_3.db',
        size: 30340,
        created_at: 1678937685,
      },
    ] as FileToImport[],
  },
  status: 200,
};

export default get;
