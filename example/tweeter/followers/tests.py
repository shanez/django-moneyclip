from django.test import TestCase
from django.core.cache import cache

from .models import Follower, Account, Tweet


class MoneyClipTest(TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        cache.clear()

        self.tom = self.create_account('tom')
        self.andy = self.create_account('andy')
        self.ann = self.create_account('ann')
        self.leslie = self.create_account('leslie')

        # Tom follows everyone
        self.follow(self.tom, self.andy)
        self.follow(self.tom, self.ann)
        self.follow(self.tom, self.leslie)

        Tweet.objects.create(text="Tweet!!!", created_by=self.tom)

    def create_account(self, username):
        account = Account(username=username)
        account.save()
        return account

    def follow(self, from_account, follow_user):
        follower = Follower()
        follower.account = follow_user
        follower.followed_by = from_account
        follower.save()
        return follower

    def test_objects_manager_returns_same_as_cached_manager(self):
        # Make sure all the usernames are the same
        for i in xrange(1, 4):
            self.assertEqual(Account.objects.get(id=i).username, Account.cache.get(id=i).username, msg="Failed on id - %i" % (i, ))

    def test_created_by_foreign_key_returns_same_model_as_direct_lookup(self):
        tweet = Tweet.objects.get(id=1)

        account = Account.objects.get(id=tweet.created_by.id)
        self.assertEqual(account.username, tweet.created_by.username)

    def test_created_by_foreign_key_returns_correct_model_after_save(self):
        tweet = Tweet.objects.get(id=1)

        account = Account.cache.get(id=tweet.created_by_id)
        account.username = 'tom haverford'
        account.save()

        self.assertEqual(account.username, Tweet.cache.get(id=1).created_by.username)

    def test_followers_count_returns_correct_value(self):
        self.assertEqual(1, self.leslie.followers_count())

    def test_followers_count_updates_when_followers_change(self):
        self.assertEqual(1, self.leslie.followers_count())

        self.follow(self.andy, self.leslie)

        self.assertEqual(2, self.leslie.followers_count())


