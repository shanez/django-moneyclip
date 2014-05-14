from functools import wraps
import logging

from django.db import models

from .machine import CacheMachine


logger = logging.getLogger('cache')


def moneyclip(cache_key, cache_fn, invalidate_class=None, invalidate_reverse=None, timeout=0, symmetrical=False):
    ''' Take any function with just args and define a cache_key and lambda for that
        cache key and this will cache the result from that function

        cache_key = string to be filled in by cache_fn
        cache_fn = fn with return of a tuple applied to cache_key
        invalidate_class = Watch class for signal
        invalidate_reverse = How to discompose signaled instance to invalidate cache
        timeout - cache timeout
        symmetrical - True - invalidate forwards and backwards

        '''
    def wrap(fn):

        @wraps(fn)
        def bypass(*args):
            ''' Runs the function that moneyclip is wrapping '''
            return fn(*args)

        def wrapper(*args):
            key = cache_key % cache_fn(*args)
            val = CacheMachine.get(key)
            if val is None:
                val = bypass(*args)
                CacheMachine.set(key, val, cache_timeout=timeout)
            return val

        def invalidate_with_reverse(*args):
            ''' Invalidates fowards and reverse

                Useful if are_friends(account_1, account_2) == are_friends(account_2, account_1)
            '''
            if invalidate_reverse:
                key_args = invalidate_reverse(*args)
            invalidate(*key_args)
            if symmetrical:
                if symmetrical is True:
                    key_args = list(key_args)
                    key_args.reverse()
                else:
                    # We passed in a function
                    key_args = symmetrical(*args)
                invalidate(*key_args)

        def invalidate(*args):
            ''' Updates the value in cache '''
            key = cache_key % cache_fn(*args)
            logger.info("Invalidating moneyclip - %s" % key)
            val = bypass(*args)
            CacheMachine.set(key, val)

        wrapper.invalidate = invalidate

        def invalidate_signal(instance, raw=False, *signal_args, **signal_kwargs):
            if not raw:
                logger.info("Invalidate moneyclip signal -- %s" % (cache_key,))
                invalidate_with_reverse(instance)


        if invalidate_class:
            def add_signals(invalidate_cls):
                ''' Adds invalidation signals for the models we are watching '''
                models.signals.post_save.connect(invalidate_signal, sender=invalidate_cls, dispatch_uid='create_'+cache_key, weak=False)
                models.signals.post_delete.connect(invalidate_signal, sender=invalidate_cls, dispatch_uid='delete_'+cache_key, weak=False)

            def create_moneyclip_signals(sender, **signal_kwargs):
                ''' Signal used if the class name is a string and is referenced before it is declared '''
                invalidate_cls = invalidate_class
                appname, model = invalidate_cls.split('.')
                if sender._meta.app_label.lower() == appname.lower() and sender._meta.module_name.lower() == model.lower():
                    invalidate_cls = sender
                    add_signals(invalidate_cls)

            if isinstance(invalidate_class, str):
                # We should try to get the ContentType here incase the class has already been prepared
                models.signals.class_prepared.connect(create_moneyclip_signals, weak=False)
            else:
                add_signals(invalidate_class)
        else:
            logger.info("Invalidation for %s has not been declared" % cache_key)

        return wrapper
    return wrap

