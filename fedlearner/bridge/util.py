# -*- coding: utf-8 -*-

def _method_encode(s):
    if isinstance(s, bytes):
        return s
    else:
        return s.encode('utf8')

def _method_decode(b):
    if isinstance(b, bytes):
        return b.decode('utf-8', 'replace')
    return b
