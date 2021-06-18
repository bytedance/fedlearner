import logging
import os
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow.compat.v1 import gfile

from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


def _generate_parquet_files(output_dir,
                            schema,
                            data,
                            num_partitions):
    names = schema.names
    chunk_size = (len(data) + 1) // num_partitions
    output_files = []
    for i in range(num_partitions):
        output_path = os.path.join(output_dir, str(i))
        data_dict = {name: [] for name in names}
        start_idx = i * chunk_size
        end_idx = min((i+1) * chunk_size, len(data))
        chunk = data[start_idx:end_idx]
        for value in chunk:
            for i in range(len(names)):
                data_dict[names[i]].append(value[i])

        table = pa.Table.from_pydict(data_dict, schema=schema)
        if not gfile.Exists(os.path.dirname(output_path)):
            gfile.MakeDirs(os.path.dirname(output_path))
        pq.write_table(table, output_path, compression="GZIP")
        output_files.append(output_path)
    return output_files


class ParquetVisitorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._input_dir = "./parquet_visitor_test"
        self._num_data = 100
        self._num_partitions = 10
        self._schema = pa.schema([
            ("k1", pa.int32()),
            ("k2", pa.int64()),
            ("k3", pa.string()),
            ("k4", pa.binary()),
        ])
        self._data = []
        for i in range(self._num_data):
            self._data.append([
                i, i, str(i), str(i).encode()
            ])
        self._input_files = _generate_parquet_files(
            self._input_dir, self._schema, self._data, self._num_partitions)

    def tearDown(self) -> None:
        if gfile.Exists(self._input_dir):
            gfile.DeleteRecursively(self._input_dir)

    def test_read_all(self):
        batch_size = 2
        visitor = ParquetVisitor(self._input_files, batch_size)
        wanted_value = 0
        for batch_data in visitor:
            self.assertEqual(self._schema, batch_data.schema)
            self.assertEqual(batch_data.num_rows, batch_size)
            values = batch_data.column(self._schema.names[0]).to_pylist()
            for v in values:
                self.assertEqual(v, wanted_value)
                wanted_value += 1

    def test_read_part_columns(self):
        batch_size = 2
        wanted_columns = ["k2", "k4"]
        wanted_schema = pa.schema([
            self._schema.field_by_name("k2"),
            self._schema.field_by_name("k4"),
        ])
        visitor = ParquetVisitor(self._input_files, batch_size, wanted_columns)
        wanted_value = 0
        for batch_data in visitor:
            self.assertEqual(wanted_schema, batch_data.schema)
            self.assertEqual(batch_data.num_rows, batch_size)
            k2_values = batch_data.column(wanted_columns[0]).to_pylist()
            k4_values = batch_data.column(wanted_columns[1]).to_pylist()
            for idx in range(len(k2_values)):
                self.assertEqual(k2_values[idx], wanted_value)
                self.assertEqual(k4_values[idx], str(wanted_value).encode())
                wanted_value += 1


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()

