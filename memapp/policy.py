import logging
import sys
import random


def random_replacement(memcache, memcache_size, max_size, key, value):
    new_size_in_mb = round(sys.getsizeof(value) / (1024 * 1024), 5)
    if new_size_in_mb > max_size:
        logging.info("Image too large for cache!")
        return False, memcache_size
    while memcache_size + new_size_in_mb > max_size:
        logging.info("Removing random item to make room in memcache...")
        random_key = random.choice(list(memcache.keys()))
        random_value = memcache.pop(random_key)
        random_size = round(sys.getsizeof(random_value) / (1024 * 1024), 5)
        memcache_size -= random_size
    memcache[key] = value
    new_memcache_size = memcache_size + new_size_in_mb
    logging.info(f"Returning new memcache_size = {new_memcache_size} and new num_items = {len(memcache)}")
    return True, new_memcache_size


def lru_replacement(memcache, memcache_size, max_size, key, value):
    new_size_in_mb = round(sys.getsizeof(value) / (1024 * 1024), 5)
    if new_size_in_mb > max_size:
        logging.info("Image too large for cache!")
        return False, memcache_size
    while memcache_size + new_size_in_mb > max_size:
        logging.info(f"{memcache_size} + {new_size_in_mb} > {max_size}")
        logging.info("Removing least recently used item to make room in memcache...")
        least_recently_used_item = memcache.popitem(last=False)
        logging.info(f"Least Recently Used Item")
        least_recently_used_size = round(sys.getsizeof(least_recently_used_item[1]) / (1024 * 1024), 5)
        logging.info(f"Least Recently Used Item Size : {least_recently_used_size}")
        memcache_size -= least_recently_used_size
        logging.info(f"updated memcache size : {memcache_size}")
    memcache[key] = value
    new_memcache_size = memcache_size + new_size_in_mb
    logging.info(f"Returning new memcache_size = {new_memcache_size} and new num_items = {len(memcache)}")
    return True, new_memcache_size


def random_resize(memcache, memcache_size, max_size):
    if memcache_size <= max_size:
        return memcache_size
    else:
        while memcache_size > max_size and len(memcache) > 0:
            logging.info("Removing random item to make room in memcache...")
            random_key = random.choice(list(memcache.keys()))
            random_value = memcache.pop(random_key)
            random_size = round(sys.getsizeof(random_value) / (1024 * 1024), 5)
            memcache_size -= random_size
        return memcache_size


def lru_resize(memcache, memcache_size, max_size):
    if memcache_size <= max_size:
        return memcache_size
    else:
        while memcache_size > max_size and len(memcache) > 0:
            logging.info("Removing least recently used item to make room in memcache...")
            least_recently_used_item = memcache.popitem(last=False)
            least_recently_used_size = round(sys.getsizeof(least_recently_used_item) / (1024 * 1024), 5)
            memcache_size -= least_recently_used_size
        return memcache_size
