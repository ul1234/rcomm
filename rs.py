#!/usr/bin/python
# -*- coding: utf-8 -*-

import unireedsolomon as rs
import numpy as np

class RsCode:
    def __init__(self, n, k):
        assert n > k
        self.coder = rs.RSCoder(n, k)
        self.block_size = n
        self.payload_size = k
        self.bytes_size = 8
        
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
        data_encoded = []
        for i in range(data_bytes.shape[0]):
            #print('data_bytes:', data_bytes[i, :])
            #data_encoded += self.coder.encode(data_bytes[i, :])
            data_encoded += self.coder.encode_fast(data_bytes[i, :])
        data_encode_bit = np.array([('00000000' + bin(ord(i))[2:])[-8:] for i in data_encoded])
        data_encode_bit = np.array([int(i) for i in ''.join(data_encode_bit)])
        #print(len(data_encode_bit))
        #print(data_encode_bit)
        return data_encode_bit
        
    def decode(self, data_bit):
        assert (len(data_bit)/self.bytes_size) % self.block_size == 0, 'data len: %d, block_size: %d' % (len(data_bit), self.block_size)
        data_bytes = data_bit.reshape(-1, self.bytes_size)@np.flipud(2**np.array(range(self.bytes_size)))
        data_bytes = data_bytes.reshape(-1, self.block_size)
        data_decoded = []
        
        for i in range(data_bytes.shape[0]):
            #print('data_bytes:', data_bytes[i, :])
            try:
                #d = self.coder.decode(data_bytes[i, :])[0]
                d = self.coder.decode_fast(data_bytes[i, :])[0]
            except:
                print('Warning: decode block fail!')
                d = '\0'*self.payload_size
            padding_size = self.payload_size - len(d)
            if padding_size > 0: d = '\0'*padding_size + d
            #print('d:', repr(d))
            data_decoded += d
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
        
if __name__ == '__main__':
    coder = RsCode(255, 223)
    data = np.array(range(500))
    data = np.array([('00000000' + bin(i)[2:])[-8:] for i in data])
    data = np.array([int(i) for i in ''.join(data)])
    print('input size: %d, data' % len(data), data[:20])
    enc_data = coder.encode(data)
    print('encode size: %d, data' % len(enc_data), enc_data[:20])
    enc_data[::75] = 0
    dec_data = coder.decode(enc_data)
    dec_data = dec_data[:len(data)]
    err = dec_data - data
    print('Error: %d' % np.sum(np.abs(err)))
    print('Data size: %d, data ' % len(dec_data), dec_data[:20])
    

