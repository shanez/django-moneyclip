from django.db import models

from .machine import CacheMachine


class PickleFieldCache(models.Model):
    class Meta:
        abstract = True
    _cached_fields = []


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

