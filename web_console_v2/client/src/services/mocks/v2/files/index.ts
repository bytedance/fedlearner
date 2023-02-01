import { FileToImport } from 'typings/dataset';

const get = {
  data: {
    data: [
      {
        path: '/root/admin/rw_datas/f_1.db',
        size: 123456,
        mtime: 1601937685,
      },
      {
        path: '/root/admin/rw_datas/f_2.db',
        size: 445678,
        mtime: 1678937685,
      },
      {
        path: '/root/admin/fl_datas/f_3.db',
        size: 30340,
        mtime: 1678937685,
      },
    ] as FileToImport[],
  },
  status: 200,
};

export const post = {
  data: {
    data: {
      uploaded_files: [
        {
          display_file_name: 'mock-file.tar.gz',
          internal_path:
            'hdfs:///home/byte_aml_tob/fedlearner_v2/upload/20211015_041720010240/mock-file.tar.gz',
        },
      ],
    },
  },
  status: 200,
};

export default get;
