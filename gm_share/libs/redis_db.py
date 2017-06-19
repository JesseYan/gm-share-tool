from django.conf import settings
import redis


db = redis.StrictRedis(
    host=settings.REDIS_CONFIG['host'],
    port=settings.REDIS_CONFIG['port'],
    db=settings.REDIS_CONFIG['db']
)
