import os


E1 = 'singly_encrypted'
E2 = 'doubly_encrypted'
E3 = 'triply_encrypted'
E4 = 'quadruply_encrypted'


class Paths:
    @staticmethod
    def base_dir() -> str:
        return os.path.join(os.environ['STORAGE_ROOT_PATH'], 'psu')

    @staticmethod
    def encode_master_meta_path(phase: str):
        return os.path.join(Paths.base_dir(), phase, 'meta.json')

    @staticmethod
    def encode_diff_output_paths():
        right = os.path.join(Paths.base_dir(), 'right_diff')
        left = os.path.join(Paths.base_dir(), 'left_diff')
        return right, left

    @staticmethod
    def encode_union_output_path():
        return os.path.join(Paths.base_dir(), 'union')

    @staticmethod
    def encode_keys_path(key_type: str):
        return os.path.join(Paths.base_dir(), 'keys', key_type)

    @staticmethod
    def encode_e2_dir():
        return os.path.join(Paths.base_dir(), E2)

    @staticmethod
    # encrypt phase & sync phase output path
    def encode_e2_file_path(file_id: [int, str]):
        return os.path.join(Paths.encode_e2_dir(), str(file_id) + '.parquet')

    @staticmethod
    def encode_e4_dir():
        return os.path.join(Paths.base_dir(), E4)

    @staticmethod
    # encrypt phase output path
    def encode_e4_file_path(file_id: [int, str]):
        return os.path.join(Paths.encode_e4_dir(), str(file_id) + '.parquet')
