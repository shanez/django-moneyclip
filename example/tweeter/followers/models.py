from django.db import models

from moneyclip.decorators import moneyclip
from moneyclip.models import CachedForeignKey, CacheMixin
from moneyclip.managers import CacheManager


class Follower(models.Model):
    account = models.ForeignKey('followers.Account', related_name='following')
    followed_by = models.ForeignKey('followers.Account', related_name='follower')


class Account(CacheMixin, models.Model):
    username = models.CharField(max_length=32)

    objects = models.Manager()
    cache = CacheManager()

    @moneyclip('account::followers::account-id-%s', lambda account: (account.id,), Follower, lambda follower: (follower.account, ))
    def followers_count(self):
        ''' Function result is cached by moneyclip and only recalculated if a Follower with the account.id == self.id is saved or deleted '''
        return self.following.count()


class Tweet(CacheMixin, models.Model):
    text = models.TextField()

    created_by = CachedForeignKey('followers.Account')

    objects = models.Manager()
    cache = CacheManager()

