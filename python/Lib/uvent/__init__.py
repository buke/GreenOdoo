# coding=utf8

# Copyright (C) 2012 Saúl Ibarra Corretgé <saghul@gmail.com>
#

__all__ = ['install']
__version__ = '0.3.0'


# Patchers

def patch_loop():
    from .loop import UVLoop
    from gevent.hub import Hub
    from gevent.resolver_thread import Resolver
    Hub.loop_class = UVLoop
    # The c-ares based resolver cannot be used for the moment
    Hub.resolver_class = Resolver


def install():
    patch_loop()

