# -*- coding: utf-8 -*-
"""Dictionary utility class

Description
-----------

Utility class for URL.

Libraries/Modules
-----------------

- None.
    
Notes
-----

- None.

Author(s)
---------

- Created by Sandro Moretti on 06/06/2022.
  Dedagroup Spa.

Members
-------
"""
import collections

# 
#-----------------------------------------------------------
class Hasher(dict):
    
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

# 
#-----------------------------------------------------------
class AttributeDict(dict):
    """Subclass of dict which allows attribute lookup for keys""" 
    def __getattr__(self, name):
        try:
            value = self[name]
            return value if not isinstance( value, dict ) \
                else AttributeDict( value )
        except:
            return None
    
# 
#-----------------------------------------------------------
class VirtDict(dict):
    """
    Virtual dictionary that return always values
    """
    
    def __init__(self, _dict=None, _defaultValue=''):
        _dict = _dict if isinstance(_dict, dict) else {}
        self._defaultValue = _defaultValue
        super(VirtDict, self).__init__( _dict )
        
    
    def __missing__(self, key):
        return self._defaultValue

# 
#-----------------------------------------------------------
class dictUtil:
        
    
    @staticmethod
    def substituteVariables(d, variables):
        """
        Utility function to substitute dictionary values defined as variables 
        using the format: key: {var_name}
        
        :param d: Dictionary with values assigned as variable.
        :type d: dict
    
        :param variables: Dictionary containing variables name: value.
        :type variables: dict
        """
        try:
            stack = []
            stack.append(d)
            while stack:
                dd = stack.pop()
                for k, v in dd.items():
                    if isinstance(v, dict):
                        stack.append(v) 
                        
                    elif isinstance(v, str):
                        dd[k] = v.format(**variables)
                        
                    elif isinstance(v, list):
                        for i in range( len(v) ):
                            if isinstance(v[i], str):
                                v[i] = v[i].format(**variables)
            return d
        except KeyError as e:
            raise Exception( "Undefined variable: {0}".format( str(e) ) )

    
    @staticmethod
    def merge(d1, d2, *dn):
        """
        Utility function to merge two or more dictionaries
        
        :param d1: first dictionary
        :type: dict
    
        :param d2: second dictionary
        :type: dict
        
        :param dn: n optional dictionaries
        :type: list of dictionaries
        
        """
        d1 = d1 or {}
        d2 = d2 or {}
        dict_res = {**d1 , **d2}
        for d in dn:
            d = d or {}
            dict_res = {**dict_res, **d}
        return dict_res
    
    
    @staticmethod
    def dict_merge(dct, merge_dct):
        """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
        updating only top-level keys, dict_merge recurses down into dicts nested
        to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
        ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        """
        for k, v in merge_dct.items():
            if (k in dct and isinstance(dct[k], dict)
                    and isinstance(v, collections.Mapping)):
                dictUtil.dict_merge(dct[k], v)
            else:
                dct[k] = v
                
        return dct
    
    
    @staticmethod
    def isSubset(subset, superset):
        """
        Utility function to check if a dictionary is a subset of another
        
        :param subset: subset dictionary
        :type: dict
    
        :param superset: superset dictionary
        :type: dict
        """
        return all( item in superset.items() for item in subset.items() )
    
    
    @staticmethod
    def subset(superset, keys, asString=False):
        """
        Utility function to get a subset of a dictionary
        
        :param superset: a dictionary
        :type: dict
    
        :param keys: an iterable object contaings the result keys; can be 
               a string with keys separated by comma
        :type: iterable; string
        """
        if not superset:
            return None
        
        # create a set from string
        if isinstance( keys, str ):
            keys = [ k.strip() for k in str( keys ).split( ',' ) ]
            
        if not keys:
            return None
        
        if asString:
            return { k: str(superset[k]) for k in superset.keys() & keys }
            
        return { k: superset[k] for k in superset.keys() & keys }
    
    
    @staticmethod
    def equal_values(d1: dict, d2: dict, keys: list) -> bool:
        """
        Utility function to compare two dictionaries by a set of keys
        
        :param d1: firt dictionary
        :type: dict
        
        :param d1: second dictionary
        :type: dict
    
        :param keys: an iterable object contaings the result keys; can be 
               a string with keys separated by comma
        :type: iterable; string
        """
        d1 = d1 or {}
        d2 = d2 or {}
        
        # create a set from string
        if isinstance( keys, str ):
            keys = [ k.strip() for k in str( keys ).split( ',' ) ]
            
        if not keys:
            return False
        
        for k in keys:
            k = str(k)
            if str(d1.get( k, -1 )) != str(d2.get( k, -2 )):
                return False
            
        return True

    
    
    @staticmethod
    def virtualize(d):
        """
        Utility function to virtualize a dictionary
        ( a dictionary with always a value }
        
        :param d: a dictionary
        :type: dict
        """
        return VirtDict(d)
    
    
    @staticmethod
    def asStringExpression(d):
        if not d:
            return ''
        return ' AND '.join( [ "{0}='{1}'".format( k, v ) for k,v in d.items() ] )
    
