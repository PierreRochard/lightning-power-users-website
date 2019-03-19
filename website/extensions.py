from flask_caching import Cache
from flask_webpack import Webpack

cache = Cache(config={'CACHE_TYPE': 'simple'})

webpack = Webpack()
