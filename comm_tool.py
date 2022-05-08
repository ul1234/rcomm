#!/usr/bin/python
# -*- coding: utf-8 -*-

from img_utils import ImgUtils
import pyperclip
import time
import subprocess
import sys, os
#import win32clipboard, win32con

try:
    import win32api, win32con, win32gui
except:
    pass

def get_comm_tool(comm, print_debug = None):
    if comm == 'clip':
        c = ClipComm(print_debug)
    elif comm == 'img':
        c = ImgComm(print_debug)
    elif comm == 'img_to_file':
        c = ImgComm(print_debug, to_file = True)
    elif comm == 'img_from_file':
        c = ImgComm(print_debug, from_file = True)
    elif comm == 'interactive':
        c = InteractiveComm(print_debug)
    elif comm == 'auto':
        c = InteractiveComm(print_debug, auto_reply = True)
    else:
        raise Exception('no comm type %s' % comm)
    return c

class CommTool:
    def __init__(self, print_debug = None):
        self.print_debug = print_debug or self.print_

    def print_(self, text):
        print(text)

    def get_max_tx_text_size(self):
        raise Exception('should implement')

    def reset_text(self):
        pass

    def empty_text(self):
        pass

    def expect_text(self, expect, cmd_to_text_func = None):
        pass

    def clear_get_text(self):
        self.reset_text()

    def close(self):
        pass

class InteractiveComm(CommTool):
    def __init__(self, print_debug = None, auto_reply = False):
        CommTool.__init__(self)
        self.auto_reply = auto_reply
        self.reset_text_count = 0
        pyperclip.set_print_debug_func(self.print_debug)

    def get_max_tx_text_size(self):
        return 1000000

    def expect_text(self, cmd, cmd_to_text_func = None):
        self.expected_cmd = cmd
        self.expected_cmd_to_text_func = cmd_to_text_func

    def get_text(self, expect_data_idx = 0, fake_func = None):
        if self.auto_reply:
            result = self.expected_cmd
        else:
            result = input('\n%s?' % self.expected_cmd)
            result = result or self.expected_cmd
        if self.expected_cmd_to_text_func: result = self.expected_cmd_to_text_func(result)
        #print('result is %s\n' % result)
        return result

    def set_text(self, text, data_idx = 0):
        if False:
            while True:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    break
                except:
                    self.print_debug('set clipboard failed, try again.')
                    time.sleep(0.5)
            win32clipboard.SetClipboardData(win32con.CF_TEXT, text)
            win32clipboard.CloseClipboard()
        else:
            pyperclip.copy(text)

    def reset_text(self):
        self.set_text('[%d]reset text...' % (self.reset_text_count))
        self.reset_text_count += 1
        time.sleep(0.2)

    def empty_text(self):
        self.set_text('')
        time.sleep(0.2)

class ClipComm(CommTool):
    def __init__(self, print_debug = None):
        CommTool.__init__(self)
        self.reset_text_count = 0
        pyperclip.set_print_debug_func(self.print_debug)

    def get_max_tx_text_size(self):
        return 1000000

    def get_text(self, expect_data_idx = 0, fake_func = None):
        try:
            if False:
                win32clipboard.OpenClipboard()
                result = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                win32clipboard.CloseClipboard()
            else:
                result = pyperclip.paste()
            return result
        except:
            self.print_debug('get clipboard failed, try again.')
            return ''

    def set_text(self, text, data_idx = 0):
        if False:
            while True:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    break
                except:
                    self.print_debug('set clipboard failed, try again.')
                    time.sleep(0.5)
            win32clipboard.SetClipboardData(win32con.CF_TEXT, text)
            win32clipboard.CloseClipboard()
        else:
            pyperclip.copy(text)

    def reset_text(self):
        self.set_text('[%d]reset text...' % (self.reset_text_count))
        self.reset_text_count += 1
        time.sleep(0.2)

    def empty_text(self):
        self.set_text('')
        time.sleep(0.2)

class ImgComm(CommTool):
    def __init__(self, print_debug = None, to_file = False, from_file = False):
        CommTool.__init__(self)
        self.img_utils = ImgUtils()
        self.max_tx_bytes = self.img_utils.get_max_text_size()
        print('max tx bytes: %d' % self.max_tx_bytes)
        self.to_file = to_file
        self.from_file = from_file
        self.img_viewer = None
        self.temp_tx_img_file = r'data\temp_tx_data.png'
        self.init_startupinfo()

    def init_startupinfo(self):
        STARTF_USESHOWWINDOW = 1
        SW_MAXIMIZE = 3
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_MAXIMIZE
        self.startupinfo = startupinfo

    def get_max_tx_text_size(self):
        return self.max_tx_bytes

    def get_text(self, expect_data_idx = 0, fake_func = None):
        time.sleep(1)    # wait 1s for other side img ready
        for times in range(10):
            #print('start to rx img')
            text = self.img_utils.get_data_from_screen(to_file = self.to_file)
            #print('img %d get %s' % (times, text))
            if text:
                if self.to_file:
                    rx_img_file = r'data\rx_data_%d.png' % expect_data_idx
                    self.img_utils.save_img_to_file(rx_img_file)
                break
            time.sleep(0.2)
        #print('img get %s' % text)
        if self.to_file and not fake_func is None:   # to file, fake the payload
            text = fake_func(text)
            #print('fake text payload.')
        return text

    def set_text(self, text, data_idx = 0):
        self.clear_set_text()
        if text:
            if self.to_file or self.from_file:
                tx_img_file = r'data\tx_data_%d.png' % data_idx
            else:
                tx_img_file = self.temp_tx_img_file
            if not self.from_file:
                self.img_utils.set_data_to_img(text, tx_img_file, data_idx)
            if not self.to_file:
                self.img_viewer = subprocess.Popen(['mspaint', tx_img_file], startupinfo = self.startupinfo)
                time.sleep(0.1)
                #print('after img show')

    def clear_set_text(self):
        if not self.img_viewer is None:
            self.img_viewer.terminate()
            self.img_viewer.wait()
            self.img_viewer = None

    def close(self):
        self.clear_set_text()
        if os.path.isfile(self.temp_tx_img_file):
            os.remove(self.temp_tx_img_file)
