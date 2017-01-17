#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
#
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import pychart_types
import types

def set_defaults(cls, **dict):
    validAttrs = getattr(cls, "keys")
    for attr, val in dict.items():
        if not validAttrs.has_key(attr):
            raise Exception, "%s: unknown attribute %s." % (cls, attr)
        tuple = list(validAttrs[attr])
        # 0 : type
        # 1: defaultValue
        # 2: document
        # 3: defaultValue document (optional)
        tuple[1] = val
        validAttrs[attr] = tuple

class T(object):
    def init(self, args):
        keys = self.keys
        for attr, tuple in keys.items():
            defaultVal = tuple[1]
            if isinstance(defaultVal, types.FunctionType):
                # if the value is procedure, use the result of the proc call
                # as the default value
                defaultVal = apply(defaultVal, ())
            setattr(self, attr, defaultVal)

        for key, val in args.items():
            self.__setattr__(key, val)

    def __check_type(self, item, value):
        if item.startswith("_"):
            return

        if not self.keys.has_key(item):
            raise Exception, "%s: unknown attribute '%s'" % (self, item)

        typeval, default_value, docstring = self.keys[item][0:3]
        if value == None or typeval == pychart_types.AnyType:
            pass
        elif typeval == bool:
            # In 2.3, bool is a full-fledged type, whereas
            # in 2.2, it's just a function that returns an integer.
            # To mask this difference, we handle the bool type specially.
            if value not in (True, False):
                raise TypeError, "%s: Expecting bool, but got %s" % (self, value)
        elif typeval == str:
            if not isinstance(value, str) and not isinstance(value, unicode):
                raise TypeError, "%s: Expecting a string, but got %s" % (self, value)
        elif isinstance(typeval, types.FunctionType):
            # user-defined check procedure
            error = apply(typeval, (value,))
            if error != None:
                raise TypeError, "%s: %s for attribute '%s', but got '%s'" % (self, error, item, value)
        elif isinstance(value, typeval):
            pass
        else:
            raise TypeError, "%s: Expecting type %s, but got %s (attr=%s, %s)"  % (self, typeval, value,  item, self.keys[item])
    def __init__(self, **args):
        self.init(args)

    def __setattr__(self, item, value):
        self.__check_type(item, value)
        self.__dict__[item] = value

    def check_integrity(self):
        for attr, value in self.__dict__.items():
            self.__check_type(attr, value)
        return True
