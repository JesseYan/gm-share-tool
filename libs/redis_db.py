import redis
from settings import settings

db = redis.StrictRedis(
    host=settings.REDIS_CONFIG['host'],
    port=settings.REDIS_CONFIG['port'],
    db=settings.REDIS_CONFIG['db']
)
