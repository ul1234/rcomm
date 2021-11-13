#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from rcomm import RComm
from comm_tool import get_comm_tool

class RCommClient(RComm):
    def __init__(self, client_to_server = 'clip', server_to_client = 'clip'):
        RComm.__init__(self)
        self.tx_prefix, self.tx_postfix = self.client_prefix, self.client_postfix
        self.rx_prefix, self.rx_postfix = self.server_prefix, self.server_postfix
        self.tx_comm_tool = get_comm_tool(client_to_server, self.print_debug)
        self.rx_comm_tool = get_comm_tool(server_to_client, self.print_debug)
        self.init_tx_rx()

if __name__ == '__main__':
    assert len(sys.argv) == 2, 'Usage: python rcomm_client.py file_or_dir'
    comm = RCommClient(client_to_server = 'img')
    print('start send %s...' % sys.argv[1])
    file = comm.enc_file([sys.argv[1]])
    comm.send_file(file)
