import os


E1 = 'singly_encrypted'
E2 = 'doubly_encrypted'
E3 = 'triply_encrypted'
E4 = 'quadruply_encrypted'


class Paths:
    @staticmethod
    def encode_union_output_paths(output_dir: str):
        right = os.path.join(output_dir, 'right_diff')
        left = os.path.join(output_dir, 'left_diff')
        return right, left

    @staticmethod
    def encode_keys_path(key_type: str):
        return os.path.join(os.environ['STORAGE_ROOT_PATH'], 'keys', key_type)
