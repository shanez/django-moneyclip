from django.db.models.query import QuerySet
from django.db import models

from .machine import CacheMachine


class CacheQuerySet(QuerySet):
    def get(self, **kwargs):
        if len(kwargs.keys()) == 0:
            raise Exception("Supply a kwarg")

        model = self.model.get_cache(**kwargs)
        if not model:
            try:
                model = super(CacheQuerySet, self).get(**kwargs)
            except self.model.DoesNotExist, e:
                self.model.set_cache(CacheMachine.DOES_NOT_EXIST, **kwargs)
                raise e

            self.model.set_cache(model, **kwargs)
        return model


class CacheManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self, *args, **kwargs):
        return CacheQuerySet(self.model)

