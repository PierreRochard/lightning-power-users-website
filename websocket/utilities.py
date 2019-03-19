import uuid

from website.constants import keyring
from website.logger import log


def get_server_id(server_name: str):
    log.debug('getting server id', server_name=server_name)
    server_id = keyring.get_password(
        service=server_name + '_server_id',
        username=server_name + '_server_id',
    )
    if server_id is None:
        log.debug('creating server id', server_name=server_name)
        server_id = uuid.uuid4().hex
        keyring.set_password(
            service=server_name + '_server_id',
            username=server_name + '_server_id',
            password=server_id
        )
    return server_id
