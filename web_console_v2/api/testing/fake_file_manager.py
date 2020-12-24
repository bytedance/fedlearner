from typing import List

from fedlearner_webconsole.utils.file_manager import FileManagerBase


class FakeFileManager(FileManagerBase):
    def can_handle(self, path: str) -> bool:
        return path.startswith('fake://')

    def ls(self, path: str, recursive=False) -> List[str]:
        return ['fake://data/f1.txt']

    def move(self, source: str, destination: str) -> bool:
        return source.startswith('fake://move')

    def remove(self, path: str) -> bool:
        return path.startswith('fake://remove')
