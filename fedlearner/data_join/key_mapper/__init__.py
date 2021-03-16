import pkgutil
import os
import inspect
import logging
import sys
import traceback

from fedlearner.data_join.key_mapper.key_mapping import BaseKeyMapper

keymapper_impl_map = {}

__path__ = pkgutil.extend_path(__path__, os.path.join(__name__, "impl"))

for _, module, ispackage in pkgutil.walk_packages(
    path=__path__, prefix=__name__+'.'):
    if ispackage:
        continue
    __import__(module)
    for _, m in inspect.getmembers(sys.modules[module], inspect.isclass):
        if not issubclass(m, BaseKeyMapper):
            continue
        keymapper_impl_map[m.name()] = m

def create_key_mapper(mapper, *args, **kwargs):
    if mapper in keymapper_impl_map:
        return keymapper_impl_map[mapper](*args, **kwargs)
    logging.fatal("Unknown key mapper%s", mapper)
    traceback.print_stack()
    os._exit(-1) # pylint: disable=protected-access
    return None
