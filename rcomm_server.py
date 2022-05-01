#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from decorator import thread_func
from rcomm import RComm
from comm_tool import get_comm_tool

class RCommServer(RComm):
    def __init__(self, client_to_server = 'clip', server_to_client = 'clip'):
        RComm.__init__(self)
        self.tx_prefix, self.tx_postfix = self.server_prefix, self.server_postfix
        self.rx_prefix, self.rx_postfix = self.client_prefix, self.client_postfix
        self.tx_comm_tool = get_comm_tool(server_to_client, self.print_debug)
        self.rx_comm_tool = get_comm_tool(client_to_server, self.print_debug)
        self.init_tx_rx()

    def receive_file(self, click_deamon = False, cont_mode = False):
        if click_deamon:
            self.override_tx_text()
            self.click_heart_beat = 1
            self.click_daemon()
        return RComm.receive_file(self, cont_mode)

    def override_tx_text(self):
        self.super_tx_text = self.rx_text
        self.rx_text = self._rx_text

    def _rx_text(self):
        if hasattr(self, 'click_heart_beat'): self.click_heart_beat = self.click_heart_beat + 1     # click deamon heart beat
        return self.super_tx_text()

    # click daemon start after 3 seconds
    @thread_func(3)
    def click_daemon(self):
        global heart_beat, heart_lost
        heart_beat = 0
        heart_lost = 0
        def heart_beat_alive(times):
            global heart_beat, heart_lost
            if self.click_heart_beat == heart_beat:
                heart_lost = heart_lost + 1
            else:
                heart_lost = 0
                heart_beat = self.click_heart_beat
            if heart_lost > times:
                return False
            return True
        print('click deamon start...')
        while heart_beat_alive(6):
            #pos = win32gui.GetCursorPos()
            #win32api.SetCursorPos(pos[0], pos[1])
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            time.sleep(0.4)
        print('click daamon end.')


if __name__ == '__main__':
    assert len(sys.argv) == 1, 'Usage: python rcomm_server.py'
    #comm = RCommServer(client_to_server = 'img')
    comm = RCommServer()
    print('start receiving...')
    file = comm.receive_file()
    comm.dec_file(file, '.')
