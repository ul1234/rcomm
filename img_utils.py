#!/usr/bin/python
# -*- coding: utf-8 -*-

import numpy as np
from PIL import Image
from pprint import pprint
import hashlib
import codecs, datetime
from decorator import time_evaluate
import rs
try:
    import pyautogui
except:
    pass

class ImgUtils:
    def __init__(self):
        self.bit_group_size = 4
        self.pixel_block_size = 1   # 1 point: 4x4 pixels
        self.pixel_width_height = [200*4, 100*4]
        # derived
        self.rgb_size = 3
        self.length_size = 32  # bit
        self.md5_size = 128  # bit
        self.rs_block_size = 255
        self.rs_payload_size = 231
        self.repeat_size = self.pixel_block_size * self.pixel_block_size
        self.mul_array = 2**np.array(range(0, self.bit_group_size))  # [1,2,4,8]
        self.factor = 256/(2**self.bit_group_size)
        self.raw_data_size = self.pixel_width_height[0] * self.pixel_width_height[1] * self.rgb_size * self.bit_group_size
        rs_code_block_num = int(self.raw_data_size / (self.rs_block_size * 8))
        self.max_data_size_before_encode = rs_code_block_num * self.rs_payload_size * 8
        self.max_data_size_after_encode = rs_code_block_num * self.rs_block_size * 8
        self.max_payload_data_size = self.max_data_size_before_encode - self.md5_size - self.length_size
        print('max data size: %d' % self.max_payload_data_size)
        self.marker_data_bit, self.marker_data_seq = self.gen_marker_data()
        self.coder = rs.RsCode(self.rs_block_size, self.rs_payload_size)

    def gen_marker_data(self):
        np.random.seed(1000)
        data_bit = np.random.randint(0,2,size=(self.pixel_width_height[0]*self.pixel_block_size, ))
        data_seq = data_bit * 255
        #print('marker data:', data_bit)
        #print('marker seq:', data_seq)
        return (data_bit, data_seq)

    def get_data(self):
        np.random.seed(10000)
        #data_size = self.max_payload_data_size
        data_size = 10
        data = np.random.randint(0,2,size=(data_size, ))
        print('data payload size: %d, data ' % len(data), data[:20])
        return data

    @time_evaluate
    def gen_data(self, data_payload):
        assert len(data_payload) <= self.max_payload_data_size, 'data_payload len %d > max_payload_data_size %d' % (len(data_payload), self.max_payload_data_size)
        # encode(length( 32 bit) + data_payload + md5 (128 bit) + padding) + padding
        data_size = len(data_payload)
        min_rs_block_num = int(np.ceil((data_size + self.length_size + self.md5_size) / (self.rs_payload_size * 8)))
        data_size_before_encode = min_rs_block_num * self.rs_payload_size * 8
        data_size_after_encode = min_rs_block_num * self.rs_block_size * 8
        padding_size = data_size_before_encode - (data_size + self.length_size + self.md5_size)
        data_size_bit = np.array([int(x) for x in bin(data_size)[2:]])
        data_size_padding_size = self.length_size - len(data_size_bit)
        data_size_bit = np.concatenate((np.zeros(data_size_padding_size), data_size_bit))
        data_payload = np.concatenate((data_size_bit, data_payload)).astype(np.int32)
        #print('data payload: ', data_payload[:50])
        md5_data = self.md5(data_payload)
        #print(data.shape, md5_data.shape)
        data_payload = np.concatenate((data_payload, md5_data, np.zeros(padding_size))).astype(np.int32)
        assert len(data_payload) == data_size_before_encode, 'data_payload %d != data_size_before_encode %d' % (len(data_payload), data_size_before_encode)
        #print('data_payload:', len(data_payload), self.max_payload_data_size, self.data_size_after_encode)
        fec_data = self.coder.encode(data_payload)
        assert len(fec_data) == data_size_after_encode, 'fec_data len %d != data_size_after_encode %d' % (len(fec_data), data_size_after_encode)
        #print('before scram:', data_payload[:20])
        data_payload = self.scramble(fec_data)
        #print(data_payload.shape, self.data_size_after_encode, self.raw_data_size)
        data_payload = np.concatenate((data_payload, self.scramble(np.zeros(self.raw_data_size-data_size_after_encode))))
        #print('after scram:', data_payload[:20])
        #print(data_payload.shape)
        assert len(data_payload) == self.raw_data_size, 'data_payload len %d != raw_data_size %d' % (len(data_payload), self.raw_data_size)
        return data_payload

    @time_evaluate
    def scramble(self, data):
        data_size = len(data)
        np.random.seed(101)
        scram_data = np.random.randint(0,2,size=(data_size, ))
        data = (data + scram_data) % 2
        data = data.astype(np.int32)
        return data

    @time_evaluate
    def md5(self, data):
        h = hashlib.md5(data).hexdigest()
        #print('md5: ', h)
        data_md5 = np.array([int(x) for x in bin(int(h, 16))[2:]]).astype(np.int32)
        md5_padding = self.md5_size - len(data_md5)
        data_md5 = np.concatenate((np.zeros(md5_padding), data_md5))
        data_md5 = data_md5.astype(np.int32)
        return data_md5

    @time_evaluate
    def encode_data(self, data, width = 0):
        #pprint(data)
        data = data.reshape(-1, self.bit_group_size)
        data = data@self.mul_array      # bit group form a value
        data = data * self.factor + self.factor/2   # in the middle of the range
        data = data.astype(np.uint8)
        #print(data)
        #print(data.shape)
        width = width or self.pixel_width_height[0]
        #print(width)
        #print(data.shape)
        data = data.repeat(self.repeat_size).reshape(self.rgb_size, -1, width, self.pixel_block_size, self.pixel_block_size)
        #pprint(data)
        #print(data.shape)
        data = data.swapaxes(2,3)  # (0,1,2,3,4) -> (0,1,3,2,4)
        data = data.reshape(self.rgb_size, -1, width * self.pixel_block_size)  # (3*H*W)
        #pprint(data)
        #print(data.shape)
        return data

    @time_evaluate
    def add_marker_data(self, data):
        #return data
        # data: (3*H*W)
        red_marker = self.marker_data_seq
        #print('red_marker:', red_marker.shape)
        #red_marker = np.ones(self.pixel_width_height[0] * self.pixel_block_size) * 255
        other_marker = np.zeros(self.pixel_width_height[0] * self.pixel_block_size * 2)
        #print('other_marker:', other_marker.shape)
        rgb_marker = np.concatenate((red_marker, other_marker))
        #print('rgb_marker:', rgb_marker.shape)
        rgb_marker = rgb_marker.reshape(self.rgb_size, 1, -1)
        rgb_marker = rgb_marker.astype(np.uint8)
        #pprint(data)
        #pprint(rgb_marker[0, 0, :])
        data = np.concatenate((rgb_marker, data), axis=1)
        #pprint(data)
        return data

    @time_evaluate
    def add_protect_data(self, data):
        #return data
        # data: (3*H*W)
        np.random.seed(10)
        #row
        protect_data = np.random.randint(0,2,size=(self.rgb_size*self.pixel_width_height[0]*self.bit_group_size, ))
        protect_data = self.encode_data(protect_data, self.pixel_width_height[0])
        protect_data = protect_data.astype(np.uint8)
        data = np.concatenate((protect_data, data), axis=1)
        # col
        num_col = self.pixel_width_height[1]+1
        protect_data = np.random.randint(0,2,size=(self.rgb_size*num_col*self.bit_group_size, ))
        protect_data = self.encode_data(protect_data, num_col)
        protect_data = protect_data.reshape(self.rgb_size, -1, self.pixel_block_size)  # 3 * H * 4
        blank_data = np.tile(np.array([0, 0, 0]), self.pixel_block_size).reshape(self.rgb_size, -1, self.pixel_block_size)   # 3 * 1 * 4
        #print(blank_data.shape, protect_data.shape)
        protect_data = np.concatenate((blank_data, protect_data), axis=1)
        #print(protect_data.shape, data.shape)
        protect_data = protect_data.reshape(self.rgb_size, -1, self.pixel_block_size)   # 3 * H * 4
        protect_data = protect_data.astype(np.uint8)
        #print(protect_data.shape, data.shape)
        data = np.concatenate((protect_data, data), axis=2)
        return data

    @time_evaluate
    def set_data_to_img(self, text, img_file):
        binary_data = self.string_to_binary(text)
        raw_data = self.gen_data(binary_data)
        enc_data = self.encode_data(raw_data)
        marker_data = self.add_marker_data(enc_data)
        protect_data = self.add_protect_data(marker_data)
        img = self.data_to_img(protect_data)
        img.save(img_file)
        #print('file %s saved!' % img_file)

    def img_to_data(self, img):
        data = np.asarray(img)
        #pprint(data)
        # data:  (H*W*3) -> (3*H*W)
        data = data.swapaxes(1,2).swapaxes(0,1).astype(np.uint8)
        #pprint(data)
        return data

    @time_evaluate
    def decode_data(self, data):
        # data:  (3*H*W)
        data = data.reshape(self.rgb_size, -1, self.pixel_block_size, self.pixel_width_height[0], self.pixel_block_size)
        data = data.swapaxes(2,3)  # (0,1,2,3,4) -> (0,1,3,2,4)
        data = data.reshape(self.rgb_size, -1, self.repeat_size)  # 3*(H*W)*16
        data = np.round(np.mean(data, 2)).reshape(-1)  # 3*(H*W)
        #print(data)
        data = np.floor(data/self.factor)
        #print(data)
        data_bit = np.array([], dtype=np.int32)
        for i in range(self.bit_group_size):
            data, remainder = divmod(data, 2)
            data_bit = np.concatenate((data_bit, remainder))
        data_bit = data_bit.reshape(self.bit_group_size, -1).transpose()
        data_bit = data_bit.reshape(-1).astype(np.int32)
        #print(data_bit)
        return data_bit

    @time_evaluate
    def data_parser(self, data_bit):
        # encode(length( 32 bit) + data_payload + md5 (128 bit) + padding) + padding
        assert len(data_bit) == self.raw_data_size, 'data_bit len %d != raw_data_size %d' % (len(data_bit), self.raw_data_size)
        #print('before scram:', data_bit[:20])
        data_bit = data_bit[:self.max_data_size_after_encode]
        data_bit = self.scramble(data_bit)
        #print('after scram:', data_bit[:20])
        first_block_data_size_after_encode = self.rs_block_size * 8
        block_decode_data = self.coder.decode(data_bit[:first_block_data_size_after_encode])
        data_size_bit = block_decode_data[:self.length_size]
        data_size = np.dot(data_size_bit, np.flipud(2**np.array(range(0, self.length_size))))
        if data_size > self.max_payload_data_size:
            print('data size error: %d.' % data_size)
            data_payload = None
        else:
            rs_block_num = int(np.ceil((data_size + self.length_size + self.md5_size) / (self.rs_payload_size * 8)))
            data_size_before_encode = rs_block_num * self.rs_payload_size * 8
            data_size_after_encode = rs_block_num * self.rs_block_size * 8
            if rs_block_num > 1:
                next_block_decode_data = self.coder.decode(data_bit[first_block_data_size_after_encode:data_size_after_encode])
                block_decode_data = np.concatenate((block_decode_data, next_block_decode_data)).astype(np.int32)
            assert len(block_decode_data) == data_size_before_encode, 'block_decode_data len %d != data_size_before_encode %d' % (len(block_decode_data), data_size_before_encode)
            block_decode_data = block_decode_data[:data_size + self.length_size + self.md5_size]
            rx_data_payload = block_decode_data[:-self.md5_size]
            rx_md5_data = block_decode_data[-self.md5_size:]
            md5_data = self.md5(rx_data_payload)
            #print('rx_md5_data:', rx_md5_data)
            #print('md5_data:', md5_data)
            #print('rx data payload: ', data_bit[:50])
            check_pass = np.sum(np.abs(md5_data - rx_md5_data)) == 0
            #check_pass = True
            if check_pass:
                data_payload = rx_data_payload[self.length_size:]
            else:
                data_payload = None
                print('check md5 fail, rx md5 != md5, ', rx_md5_data, md5_data)
        return data_payload

    @time_evaluate
    def get_data_by_marker(self, data):
        # 3 * H * W
        _, H, W = data.shape
        data = data.astype(np.int32)
        marker_seq = self.marker_data_seq.astype(np.int32) - 128
        data_seq = data[0,:,:].reshape(-1) - 128
        conv = np.convolve(data_seq, np.flipud(marker_seq), 'valid') / marker_seq.size
        conv = conv.astype(np.int32)
        index = np.argmax(conv)
        #print(conv[index-10:index+10])
        #print(conv[0:index+10])
        #pprint(marker_seq[0:20])
        #pprint(data_seq[index:index+20])
        row_index, col_index = divmod(index, W)
        #print('row index %d, col index %d, max value %d' % (row_index, col_index, conv[index]))
        if conv[index] < 10000:
            return None
        else:
            data = data[:, row_index:row_index+self.pixel_width_height[1]*self.pixel_block_size+1, col_index:col_index+self.pixel_width_height[0]*self.pixel_block_size]
            #img = self.data_to_img(data)
            #img.show()
            # 3 * H * W, remove marker
            #data = data[:, 1:, :]

            #print('data:\n', data.shape, data[0, 0:10, 0:10])
            return data

    @time_evaluate
    def remove_marker_data(self, data):
        data = data[:, 1:, :]
        return data

    def get_data_from_screen(self):
        rx_raw_data = self.get_screen()
        rx_marker_data = self.get_data_by_marker(rx_raw_data)
        #print('rx_marker_data:', rx_marker_data.shape)
        if not rx_marker_data is None:
            rx_data = self.remove_marker_data(rx_marker_data)
            #print('rx_data:', rx_data.shape)
            dec_data = self.decode_data(rx_data)
            #print('dec_data:', dec_data.shape)
            dec_data_payload = self.data_parser(dec_data)
            #print('dec_data_payload:', dec_data_payload.shape)
        else:
            dec_data_payload = None
        if not dec_data_payload is None:
            text = self.binary_to_string(dec_data_payload)
            #print('img to text', text)
            return text
        return ''

    def get_max_text_size(self):
        gap = 50
        return int(self.max_payload_data_size / 8) - gap

    @time_evaluate
    def string_to_binary(self, text):
        b = [('0000' + bin(int(i, 16))[2:])[-4:] for i in text.encode("utf-8").hex()]
        b = ''.join(b)
        data = np.array([int(i) for i in b], dtype = np.int32)
        return data

    def binary_to_string(self, data):
        hex_data = data.reshape(-1, 4)@np.array([8,4,2,1])
        data = ''.join([hex(h)[2:] for h in hex_data])
        text = codecs.decode(data, 'hex').decode("utf-8")
        return text

    def check_data(self, tx_data, rx_data):
        # 3 * H * W
        #pprint(tx_data[0, 0:20:4, 0:60:4])
        #pprint(rx_data[0, 0:20:4, 0:60:4])
        pprint(tx_data[0, -20::4, -60::4])
        pprint(rx_data[0, -20::4, -60::4])

    @time_evaluate
    def data_to_img(self, data):
        #pprint(data[0,0,:])
        # data: (3*H*W) -> (H*W*3)
        data = data.swapaxes(0,1).swapaxes(1,2).astype(np.uint8)
        #pprint(data)
        img = Image.fromarray(data, 'RGB')
        #img.save('test.png')
        #img.show()
        return img

    @time_evaluate
    def get_screen(self):
        img = pyautogui.screenshot()
        now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = 'data/screen_%s.png' % now_str
        img.save(filename)
        #print('img saved: ', filename)
        #img = Image.open('data/screen_20211112_224743.png')
        data = self.img_to_data(img)
        #print(data.shape)
        #pprint(data[0,0,:])
        return data

if __name__ == '__main__':
    img_utils = ImgUtils()
    option = 3

    if option == 1:
        data = img_utils.string_to_binary('abcdefghijklmn!@#$%')
        text = img_utils.binary_to_string(data)
        print(text)
    elif option == 2:
        raw_data = img_utils.get_data()
        raw_data = img_utils.gen_data(raw_data)
        enc_data = img_utils.encode_data(raw_data)
        marker_data = img_utils.add_marker_data(enc_data)
        protect_data = img_utils.add_protect_data(marker_data)
        img = img_utils.data_to_img(protect_data)
    else:
        raw_data = img_utils.get_data()
        raw_data = img_utils.gen_data(raw_data)
        enc_data = img_utils.encode_data(raw_data)
        marker_data = img_utils.add_marker_data(enc_data)

        rx_raw_data = img_utils.get_screen()
        rx_marker_data = img_utils.get_data_by_marker(rx_raw_data)
        if not rx_marker_data is None:
            rx_data = img_utils.remove_marker_data(rx_marker_data)
            dec_data = img_utils.decode_data(rx_data)
            dec_data_payload = img_utils.data_parser(dec_data)

            #img_utils.check_data(marker_data, rx_marker_data)
            err = dec_data - raw_data
            print('Error: %d' % np.sum(np.abs(err)))
        else:
            dec_data_payload = None
        if not dec_data_payload is None:
            print('Data size: %d, data ' % len(dec_data_payload), dec_data_payload[:20])
    print('done')

