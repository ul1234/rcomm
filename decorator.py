#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading, time

def thread_func(time_delay = 0.01):
    def _thread_func(func):
        def __thread_func(*args, **kwargs):
            def _func(*args):
                time.sleep(time_delay)
                func(*args, **kwargs)
            threading.Thread(target = _func, args = tuple(args)).start()
        return __thread_func
    return _thread_func

def use_system32_on_64bit_system(func):
    def _func(*args, **kwargs):
        import ctypes
        k32 = ctypes.windll.kernel32
        wow64 = ctypes.c_long(0)
        k32.Wow64DisableWow64FsRedirection(ctypes.byref(wow64))
        result = func(*args, **kwargs)
        k32.Wow64EnableWow64FsRedirection(wow64)
        return result
    return _func

def hook_func(target_func, before_func = None, after_func = None):
    def _func(*args, **kwargs):
        if before_func: before_func(*args, **kwargs)
        result = target_func(*args, **kwargs)
        return after_func(*args, **kwargs) if after_func else result
    return _func

def __time_evaluate_init():
    if '__time_start' not in globals():
        global __time_start
        #__time_start = time.time()
        __time_start = 0        # absolute time
    if '__nest_count' not in globals():
        global __nest_count
        __nest_count = 0
            
def _time_evaluate(func):
    def _func(*args, **kwargs):
        __time_evaluate_init()
        global __time_start, __nest_count
        
        __nest_count += 1
        leading_space = ' ' * ((__nest_count - 1) * 4)
        t0 = time.time()
        print(r'%s[%.2f][%s]------- start ----------' % (leading_space, t0-__time_start, func.__name__))
        result = func(*args, **kwargs)
        t1 = time.time()
        print(r'%s[%.2f][%s]******** end *********** %.2f seconds.' % (leading_space, t1-__time_start, func.__name__, t1-t0))
        __nest_count -= 1
        return result
    return _func

time_evaluate = lambda func: func
#time_evaluate = _time_evaluate
