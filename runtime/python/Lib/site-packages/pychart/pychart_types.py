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
import pychart_util
import types
AnyType = 9998

def IntervalType(val):
    if type(val) in (types.IntType, types.LongType,
                     types.FloatType, types.FunctionType):
	return None
    return "Expecting a number or a function"

def CoordType(val):
    if type(val) not in (types.TupleType, types.ListType):
        return "Expecting a tuple or a list"
    if len(val) != 2:
        return "Coordinate must be a pair of numbers"
    for v in val:
        if v != None and NumberType(v):
            return "Expecting a pair of numbers (got %s)" % str(v)
    return None 
    
def NumberType(val):
    if type(val) in (types.IntType, types.LongType, types.FloatType):
        return None
    else:
        return "Expecting a number"

def UnitType(val):
    if type(val) in (types.IntType, types.LongType, types.FloatType):
        return
    else:
        return "Expecting a unit"
def ShadowType(val):
    if type(val) not in (types.TupleType, types.ListType):
	return "Expecting tuple or list."
    if len(val) != 3:
	return "Expecting (xoff, yoff, fill)."
    return None

def FormatType(val):
    if type(val) in (types.StringType, types.FunctionType):
        return None
    return "Format must be a string or a function"

