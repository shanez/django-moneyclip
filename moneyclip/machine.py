from datetime import timedelta

import hashlib
import logging
import redis

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('cache')


CACHE_EXPIRATION_HOURS = getattr(settings, 'CACHE_EXPIRATION_HOURS', 12)
# When we lookup this item and see there is less than this many minutes we reload it into cache
CACHE_MITIGATE_AT_MINUTES = getattr(settings, 'CACHE_MITIGATE_AT_MINUTES', 5)



class CacheMachine(object):
    ''' Used by moneyclip and CacheMixin to store values '''
    DOES_NOT_EXIST = "DNE"

    @classmethod
    def hash(cls, key):
        return hashlib.sha224(settings.CACHE_PREFIX + key).hexdigest()

    @classmethod
    def set(cls, key, val, cache_timeout=0, expire_at=None):
        if key and not val is None:
            if not expire_at:
                expire_at = timezone.now() + timedelta(hours=CACHE_EXPIRATION_HOURS)
            set_val = (val, expire_at)
            logger.info("Setting key %s - for %s" % (key, set_val))
            try:
                cache.set(cls.hash(key), set_val, cache_timeout)
            except redis.ConnectionError, redis.ResponseError:
                logger.error("Caching backend down")

    @classmethod
    def get(cls, key, mitigation=None):
       if key:
            try:
                val_and_expiration_timestamp = cache.get(cls.hash(key))
                if val_and_expiration_timestamp:
                    val, expiration_time = val_and_expiration_timestamp
                    if val is not None:
                        logger.info("Retrieved value %s - for %s | Expire time is %s" % (val, key, expiration_time))

                        # Do herd mitigation here
                        if mitigation:
                            if expiration_time < timezone.now() + timedelta(minutes=CACHE_MITIGATE_AT_MINUTES):
                                expiration_time = timezone.now() + timedelta(minutes=CACHE_MITIGATE_AT_MINUTES+1)  # Give it one minute to run
                                cls.set(key, val, expire_at=expiration_time)
                                mitigation()

                        return val
            except redis.ConnectionError, redis.ResponseError:
                logger.error("Caching backend down")

    @classmethod
    def invalidate(cls, key):
        if key:
            value = CacheMachine.get(key)
            cache.set(cls.hash(key), value, 1)

