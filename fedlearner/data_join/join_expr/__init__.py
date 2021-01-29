import pkgutil
import os
import inspect
import logging
import sys
import traceback


from fedlearner.data_join.join_expr.key_mapping import BaseKeyMapper

keymapper_impl_map = {}

__path__ = pkgutil.extend_path(__path__, __name__)
for _, module, ispackage in pkgutil.walk_packages(
    path=__path__, prefix=__name__+'.'):
    if ispackage:
        continue
    __import__(module)
    for _, m in inspect.getmembers(sys.modules[module], inspect.isclass):
        if not issubclass(m, BaseKeyMapper):
            continue
        keymapper_impl_map[m.name()] = m

def create_example_joiner(example_joiner_options, *args, **kwargs):
    joiner = example_joiner_options.example_joiner
    if joiner in keymapper_impl_map:
        return keymapper_impl_map[joiner](
            example_joiner_options, *args, **kwargs)
    logging.fatal("Unknown key mapper%s", joiner)
    traceback.print_stack()
    os._exit(-1) # pylint: disable=protected-access
    return None
