from flask_caching import Cache
from flask_webpack import Webpack

from flask_bitcoind import BitcoindNode
from flask_lnd import LNDNode

cache = Cache(config={'CACHE_TYPE': 'simple'})

bitcoind = BitcoindNode()
lnd = LNDNode()
webpack = Webpack()
