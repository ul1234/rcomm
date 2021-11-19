#!/usr/bin/python
# -*- coding: utf-8 -*-

import unireedsolomon as rs
import numpy as np
from decorator import time_evaluate
import multiprocessing
from functools import reduce

class RsCode:
    def __init__(self, n, k):
        assert n > k
        self.coder = rs.RSCoder(n, k)
        self.block_size = n
        self.payload_size = k
        self.bytes_size = 8
        self.pool_size = 3
        self.opti = True

    @time_evaluate
    def encode(self, np_bin_array):
        self.bin_len = len(np_bin_array)
        #print('input len:', self.bin_len)
        padding_size = (self.bytes_size - self.bin_len % self.bytes_size) % self.bytes_size
        data_bit = np.concatenate((np_bin_array, np.zeros(padding_size)))
        data_bytes = data_bit.reshape(-1, self.bytes_size)@np.flipud(2**np.array(range(self.bytes_size)))
        self.data_bytes_len = len(data_bytes)
        padding_size = (self.payload_size - self.data_bytes_len % self.payload_size) % self.payload_size
        data_bytes = np.concatenate((data_bytes, np.zeros(padding_size)))
        data_bytes = data_bytes.reshape(-1, self.payload_size).astype(np.int32)
        data_encoded = self._map_encode(data_bytes) if self.opti else self._encode(data_bytes)
        data_encode_bit = np.array([('00000000' + bin(ord(i))[2:])[-8:] for i in data_encoded])
        data_encode_bit = np.array([int(i) for i in ''.join(data_encode_bit)])
        #print(len(data_encode_bit))
        #print(data_encode_bit)
        return data_encode_bit

    def _encode(self, data_bytes):
        data_encoded = []
        for i in range(data_bytes.shape[0]):
            #print('data_bytes:', data_bytes[i, :])
            #data_encoded += self.coder.encode(data_bytes[i, :])
            data_encoded += self.coder.encode_fast(data_bytes[i, :])
        return data_encoded

    def _map_encode(self, data_bytes):
        data_iter = [data_bytes[i, :] for i in range(data_bytes.shape[0])]
        pool = multiprocessing.Pool(processes = self.pool_size)
        data_encoded = pool.map(self.coder.encode_fast, data_iter)
        data_encoded = reduce(lambda x,y:x+y, data_encoded, '')
        pool.close()
        return data_encoded

    @time_evaluate
    def decode(self, data_bit):
        assert (len(data_bit)/self.bytes_size) % self.block_size == 0, 'data len: %d, block_size: %d' % (len(data_bit), self.block_size)
        data_bytes = data_bit.reshape(-1, self.bytes_size)@np.flipud(2**np.array(range(self.bytes_size)))
        data_bytes = data_bytes.reshape(-1, self.block_size)
        data_decoded = self._decode(data_bytes)
        #print('data_decoded:', data_decoded)
        #data_decoded_bytes = data_decoded[:self.data_bytes_len]
        data_decoded_bytes = data_decoded
        #print('data_decoded_bytes:', data_decoded_bytes)
        data_decode_bit = np.array([('00000000' + bin(ord(i))[2:])[-8:] for i in data_decoded_bytes])
        data_decode_bit = np.array([int(i) for i in ''.join(data_decode_bit)])
        #data_decode = data_decode_bit[:self.bin_len]
        data_decode = data_decode_bit
        #print('decoded:', data_decode)
        #print('output len:', len(data_decode))
        return data_decode

    def _decode_block(self, data_block):
        decode_success = True
        if self.decode_fail_early_quit:
            decoded_block = '\0'*self.payload_size
        else:
            try:
                #decoded_block = self.coder.decode(data_bytes[i, :])[0]
                decoded_block = self.coder.decode_fast(data_block)[0]
            except:
                #print('Warning: decode block fail!')
                self.decode_fail_early_quit = True
                decode_success = False
                decoded_block = '\0'*self.payload_size
        padding_size = self.payload_size - len(decoded_block)
        if padding_size > 0: decoded_block = '\0'*padding_size + decoded_block
        #print('decoded_block:', repr(decoded_block))
        return (decoded_block, decode_success)

    def _decode(self, data_bytes):
        self.decode_fail_early_quit = False
        data_decoded, err_blocks = self._map_decode(data_bytes) if self.opti else self._normal_decode(data_bytes)
        if err_blocks: print('Total data blocks %d. Err blocks: %s' % (data_bytes.shape[1], err_blocks))
        return data_decoded
        
    def _normal_decode(self, data_bytes):
        data_decoded = []
        err_blocks = []
        for i in range(data_bytes.shape[0]):
            decoded_block, decode_success = self._decode_block(data_bytes[i, :])
            data_decoded += decoded_block
            if not decode_success: err_blocks.append(i)
        return (data_decoded, err_blocks)

    def _map_decode(self, data_bytes):
        data_iter = [data_bytes[i, :] for i in range(data_bytes.shape[0])]
        pool = multiprocessing.Pool(processes = self.pool_size)
        data_decoded_with_flag = pool.map(self._decode_block, data_iter)
        data_decoded = reduce(lambda x,y:x+y[0], data_decoded_with_flag, '')
        err_blocks = [i for (i, (_, success)) in enumerate(data_decoded_with_flag) if not success]
        pool.close()
        return (data_decoded, err_blocks)


if __name__ == '__main__':
    coder = RsCode(255, 223)
    data = np.array(range(100000))
    data = np.array([('00000000' + bin(i)[2:])[-8:] for i in data])
    data = np.array([int(i) for i in ''.join(data)])
    print('input size: %d, data' % len(data), data[:20])
    enc_data = coder.encode(data)
    print('encode size: %d, data' % len(enc_data), enc_data[:20])
    enc_data[::200] = 0
    dec_data = coder.decode(enc_data)
    dec_data = dec_data[:len(data)]
    err = dec_data - data
    print('Error: %d' % np.sum(np.abs(err)))
    print('Data size: %d, data ' % len(dec_data), dec_data[:20])


