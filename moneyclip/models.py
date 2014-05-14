import logging

from django.db import models

from .machine import CacheMachine

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^mixins\.django\.cache\.CachedForeignKey"])
    add_introspection_rules([], ["^mixins\.django\.cache\.CachedOneToOneField"])
except ImportError:
    pass

logger = logging.getLogger('cache')


class CacheMixin(models.Model):
    class Meta:
        abstract = True

    CACHE = {}

    def save(self, *args, **kwargs):
        super(CacheMixin, self).save(*args, **kwargs)

        # Remove any cached foreign keys
        for field in self._meta.fields:
            if isinstance(field, CachedForeignKey):
                delattr(self, '_%s_cache' % (field.name,))

        self.__class__.set_cache(self, id=self.id)

    def delete(self, *args, **kwargs):
        super(CacheMixin, self).delete(*args, **kwargs)
        self.__class__.set_cache(CacheMachine.DOES_NOT_EXIST, id=self.id)

    @classmethod
    def invalidate_cache(cls, **kwargs):
        CacheMachine.invalidate(cls.cache_key(**kwargs))

    @classmethod
    def set_cache(cls, value, cache_timeout=0, **kwargs):
        if value != CacheMachine.DOES_NOT_EXIST:
            setattr(value, 'is_cached', True)
        CacheMachine.set(cls.cache_key(**kwargs), value, cache_timeout=cache_timeout)

    @classmethod
    def wrap_for_mitigation(cls, **kwargs):
        ''' Returns a function that if called will push the current value back into cache for a specified time while it calculates the new result.
            This allows mitigating of the herd
        '''
        def mitigate(cache_timeout=0):
            cls.set_cache(cls.objects.get(**kwargs), cache_timeout=cache_timeout, **kwargs)
        return mitigate

    @classmethod
    def get_cache(cls, **kwargs):
        if len(kwargs.keys()) > 1:
            raise Exception("CacheMachine can only handle 1 kwarg")
        val = CacheMachine.get(cls.cache_key(**kwargs), mitigation=cls.wrap_for_mitigation(**kwargs))
        if val == CacheMachine.DOES_NOT_EXIST:
            raise cls.DoesNotExist
        elif hasattr(val, 'reset'):
            val.reset()   # Clear any cached changes
        return val

    @classmethod
    def cache_key(cls, **kwargs):
        ''' Builds the key that is used to refrence a model by the kwargs provided '''
        filter_key = kwargs.keys()[0]
        if 'id' in filter_key or 'pk' in filter_key:  # Default caching for id
            filters = filter_key.split('__')
            length = len(filters)
            if length == 2:
                # Bypass for Django's related field looks
                if filters[1] == 'exact':
                    filter_key = filters[0]
                    length = 1
            if length == 1:
                return '%s.%s::%s' % (cls.__module__, cls.__name__, kwargs.get(filter_key))
        else:
            func = cls.CACHE.get(filter_key)
            if func:
                return func(**kwargs)


class CachedForeignKey(models.ForeignKey):
    def contribute_to_class(self, cls, name):
        super(CachedForeignKey, self).contribute_to_class(cls, name)
        setattr(cls, self.name, CachedReverseSingleRelatedObjectDescriptor(self))


class CachedOneToOneField(models.OneToOneField, CachedForeignKey):
    ''' Does not cache the reverse relationship '''
    pass


class CachedReverseSingleRelatedObjectDescriptor(models.fields.related.ReverseSingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        rel_obj = None

        try:
            rel_obj = getattr(instance, self.cache_name)
        except AttributeError:
            model = self.field.related.parent_model
            model_has_cache = hasattr(model, 'cache')
            lookup_id = getattr(instance, self.field.name+'_id')

            # if getattr(instance, is_cached, True):
            if lookup_id:
                if model_has_cache:
                    try:
                        rel_obj = model.get_cache(id=lookup_id)
                    except model.DoesNotExist:
                        pass

                    if rel_obj:
                        setattr(instance, self.cache_name, rel_obj)

                if not rel_obj:
                    rel_obj = super(CachedReverseSingleRelatedObjectDescriptor, self).__get__(instance, instance_type=instance_type)

                    # if getattr(instance, is_cached, False):
                    if model_has_cache:
                        model.set_cache(rel_obj, id=lookup_id)

        if rel_obj == CacheMachine.DOES_NOT_EXIST:
            raise self.field.related.model.DoesNotExist
        else:
            return rel_obj

