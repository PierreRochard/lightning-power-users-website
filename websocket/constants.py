from websocket.utilities import get_server_id

MAIN_SERVER_WEBSOCKET_URL = 'wss://lightningpowerusers.com:8765'

CHANNEL_OPENING_SERVER_WEBSOCKET_URL = 'ws://localhost:8710'

PUBKEY_LENGTH = 66

INVOICES_SERVER_ID = get_server_id('invoices')
CHANNELS_SERVER_ID = get_server_id('channels')
