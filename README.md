MoneyClip
=========

Django library that allows for effortless caching and invalidation of models.

Dependent on Redis

# Install

pip install django-moneyclip


# Decorator

```
from moneyclip.decoractors import moneyclip

class Follower(models.Model):
    account = models.ForeignKey('acccounts.Account')


class Account(models.Model):
    username = models.CharField(max_length=32)

    @moneyclip('account::followers::account-id-%s', lambda account: (account.id,), Follower, lambda follower: (follower.account, ))
    def followers_count(self):
        ''' Function result is cached by moneyclip and only recalculated if a Follower with the account.id == self.id is saved or deleted '''
        return self.followers_set.count()

```

## moneyclip Parameters
### Key String
A string that can be populated by Key Function that uniquely references the model
### Key Function
A function that will return a tuple which can be applied to Key String
### Invalidation Model
The model that will be monitored to signal an update to this function
### Invalidation Path
Given an instance of the invalidation model return a tuple that will be passed into the Key Function


# CacheMixin


```
from moneyclip.models import CacheMix, CachedForeignKey
from moneyclip.managers import CacheManager

class Document(CacheMixin, models.Model):
    text = models.TextField()

    book = models.ForeignKey('books.Book')
    created_by = CachedForeignKey('users.User')

    objects = models.Manager()
    cache = CacheManager()


document = Document.objects.get(id=1)   # Not cached - Using default manager

document = Document.objects.get(id=1)     # Cached
document = Document.objects.filter(id=1)[0]  # Filters are not cached

document = Document.objects.get(id=1)
document.created_by             # Cached  - Using CachedForeignKey
document.book                       # Not Cached

```

# Thoughts and notes
* The idea behind this library is the person or request that is modifying any of these values should be responsible for repopulating the cache with those values.  This allows all subsequent requests to be fulfilled from cache.
* Django's signals work off of saves and deletes, because of this you should not use 'Model.objects.update' or 'Model.objects.delete' as these methods will not fire signals.  In order to use this library you need to make certain architecture decissions.  In a future version the Manger should catch updates and deletes and invalidate all the associated keys.
* The manager must be called cache for reverse lookups to work.


# Future releases
* More documentation
* Test Cases
* update / delete invalidation
