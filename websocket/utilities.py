import uuid

from website.constants import keyring
from website.logging import log


def get_server_key(server_name: str):
    log.debug('getting server key', server_name=server_name)
    server_key = keyring.get_password(
        service=server_name + '_server_key',
        username=server_name + '_server_key',
    )
    if server_key is None:
        log.debug('creating server key', server_name=server_name)
        server_key = uuid.uuid4().hex
        keyring.set_password(
            service=server_name + '_server_key',
            username=server_name + '_server_key',
            password=server_key
        )
    return server_key
