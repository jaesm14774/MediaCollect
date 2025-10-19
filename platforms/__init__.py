"""
社群媒體平台收集器模組
"""
from .instagram_collector import InstagramCollector
from .facebook_collector import FacebookCollector
from .twitter_collector import TwitterCollector
from .threads_collector import ThreadsCollector

__all__ = [
    'InstagramCollector',
    'FacebookCollector',
    'TwitterCollector',
    'ThreadsCollector'
]

