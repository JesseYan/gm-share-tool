import helios.rpc
from settings import settings


_RPC_INVOKER = helios.rpc.create_default_invoker(debug=settings.DEBUG).with_config(dump_curl=True)


def get_base_rpc_invoker():
    return _RPC_INVOKER
