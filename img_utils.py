#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    import numpy as np
except:
    print('Try: pip install numpy')
try:
    from PIL import Image
except:
    print('Try: pip install pillow')
from pprint import pprint
import hashlib
import codecs, datetime, os
from decorator import time_evaluate
import rs
try:
    import pyautogui   # only server use this to get screenshot
except:
    pass

# change the below
# pixel_width = 1200, pixel_hight = 480):   # resolution: 1366*758
# pixel_width = 1800, pixel_hight = 800):   # resolution: 1366*758
# pixel_width = 2000, pixel_hight = 1200, pixel_block_size = 6):   # resolution: 2560*1600
# pixel_width = 2450, pixel_hight = 1300, pixel_block_size = 5):   # resolution: 2560*1600
# self.pixel_block_size = 4 #4   # 1 point: 4x4 pixels

class ImgUtils:
    ONLY_CENTER_PIXELS_FOR_DECODE = True
    SAVE_SCREEN_TO_FILE = False
    SEARCH_MARKER_IN_PIXEL_RANGE = 1    # search marker in pixel range [-1, 0, 1]
    PERMUTE_ENABLE = False

    def __init__(self, pixel_width = 2450, pixel_hight = 1300, pixel_block_size = 5):   # resolution: 1366*758
        self.bit_group_size = 4 #4
        self.pixel_block_size = pixel_block_size #4   # 1 point: 4x4 pixels
        self.pixel_width_height = [int(pixel_width / self.pixel_block_size), int(pixel_hight / self.pixel_block_size)]
        self.enable_permute = ImgUtils.PERMUTE_ENABLE
        # derived
        self.rgb_size = 3
        self.length_size = 32  # bit
        self.md5_size = 128  # bit
        self.rs_block_size = 255  # bytes
        self.rs_payload_size = 231  # bytes
        self.repeat_size = self.pixel_block_size * self.pixel_block_size
        self.mul_array = 2**np.array(range(0, self.bit_group_size))  # [1,2,4,8]
        self.factor = 256/(2**self.bit_group_size)
        self.raw_data_size = self.pixel_width_height[0] * self.pixel_width_height[1] * self.rgb_size * self.bit_group_size
        rs_code_block_num = int(self.raw_data_size / (self.rs_block_size * 8))
        self.max_data_size_before_encode = rs_code_block_num * self.rs_payload_size * 8
        self.max_data_size_after_encode = rs_code_block_num * self.rs_block_size * 8
        self.max_payload_data_size = self.max_data_size_before_encode - self.md5_size - self.length_size
        print('max data size: %d' % self.max_payload_data_size)
        self.gen_marker_data()
        self.protect_data_seq_top, self.protect_data_seq_left = self.gen_protect_data()
        self.coder = rs.RsCode(self.rs_block_size, self.rs_payload_size)
        self.marker_index_found = None
        if self.enable_permute:
            self.permute_index = self._permute_index(self.raw_data_size)
            self.unpermute_index = self._unpermute_index(self.raw_data_size, self.permute_index)

    def _gen_marker_data(self, seed):
        np.random.seed(seed)
        data_bit = np.random.randint(0,2,size=(self.pixel_width_height[0]*self.pixel_block_size, ))
        red_marker = data_bit * 255
        marker_seq = (red_marker - 128).astype(np.int32)
        #print('marker data:', data_bit)
        #print('red_marker:', red_marker.shape)
        #red_marker = np.ones(self.pixel_width_height[0] * self.pixel_block_size) * 255
        other_marker = np.zeros(self.pixel_width_height[0] * self.pixel_block_size * 2)
        #print('other_marker:', other_marker.shape)
        rgb_marker = np.concatenate((red_marker, other_marker))
        #print('rgb_marker:', rgb_marker.shape)
        rgb_marker = rgb_marker.reshape(self.rgb_size, 1, -1)
        rgb_marker = rgb_marker.astype(np.uint8)
        return (marker_seq, rgb_marker)
        
    def gen_marker_data(self):
        self.marker_seq_top, self.marker_data_top = self._gen_marker_data(1000)
        self.marker_seq_bottom, self.marker_data_bottom = self._gen_marker_data(2000)
        
    def gen_protect_data(self):
        np.random.seed(10)
        #row
        protect_data = np.random.randint(0,2,size=(self.rgb_size*self.pixel_width_height[0]*self.bit_group_size, ))
        protect_data = self.encode_data(protect_data, self.pixel_width_height[0])
        protect_data_seq_top = protect_data.astype(np.uint8)
        # col
        num_col = self.pixel_width_height[1]+1
        protect_data = np.random.randint(0,2,size=(self.rgb_size*num_col*self.bit_group_size, ))
        protect_data = self.encode_data(protect_data, num_col)
        protect_data_seq_left = protect_data.reshape(self.rgb_size, -1, self.pixel_block_size)  # 3 * H * 4
        return [protect_data_seq_top, protect_data_seq_left]
        

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
        if self.enable_permute: data_payload = self.permute(data_payload)
        assert len(data_payload) == self.raw_data_size, 'data_payload len %d != raw_data_size %d' % (len(data_payload), self.raw_data_size)
        return data_payload

    @time_evaluate
    def _permute_index(self, data_size, block_size = 0):
        INVALID_DATA = -1
        block_size = block_size or int(np.sqrt(data_size))
        padding_size = int(np.ceil(data_size / block_size)) * block_size - data_size
        index  = np.concatenate((range(data_size), np.ones(padding_size, dtype=np.int32) * INVALID_DATA))
        index = index.reshape(-1, block_size).T   # transpose
        index = index.reshape(-1)
        index = list(filter(lambda x: x != INVALID_DATA, index))  # remove INVALID_DATA
        return index

    @time_evaluate
    def _unpermute_index(self, data_size, permute_index):
        unpermute_index = np.zeros((1, data_size))
        unpermute_index[0, permute_index] = np.array(range(data_size))
        unpermute_index = unpermute_index.reshape(-1).astype(np.int32)
        #print('unpermute_index:', unpermute_index)
        return unpermute_index

    @time_evaluate
    def permute(self, data):
        assert len(data) == self.raw_data_size, 'invalid data size %d to permute' % len(data)
        permute_data = data[self.permute_index]
        return permute_data

    @time_evaluate
    def unpermute(self, data):
        assert len(data) == self.raw_data_size, 'invalid data size %d to unpermute' % len(data)
        unpermute_data = data[self.unpermute_index]
        return unpermute_data

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

    def gen_calibration_data(self):
        # self.factor = 16, one Red is 256/16 = 16 points
        # we make 7 rows of pixels, [16 reds, 16 greens, 16 blues, R+G, R+B, G+B, R+G+B]
        # Red: [8, 24, 40, ..., 248], 16 reds, green and blue is 0
        # one pixel block is 16*16
        # the screen size should be H * W = [16*4, 16*16] = 64*256
        assert self.bit_group_size == 4, 'bit_group_size should be 4 in calibration.'
        assert self.pixel_block_size == 16, 'pixel_block_size should be 16 in calibration.'
        width_pixels = 16 # 256/self.factor
        height_pixels = 7
        rgb_data = np.array(range(width_pixels)).astype(np.uint8) * self.factor + self.factor/2
        zero_data = np.zeros(width_pixels)
        # 3*H*W
        red = np.concatenate((rgb_data, zero_data, zero_data, rgb_data, rgb_data, zero_data, rgb_data))
        green = np.concatenate((zero_data, rgb_data, zero_data, rgb_data, zero_data, rgb_data, rgb_data))
        blue = np.concatenate((zero_data, zero_data, rgb_data, zero_data, rgb_data, rgb_data, rgb_data))
        data = np.concatenate((red, green, blue)).astype(np.uint8)
        pprint(data)
        # replace one pixel with 16*16 block
        data = data.repeat(self.repeat_size).reshape(self.rgb_size, -1, width_pixels, self.pixel_block_size, self.pixel_block_size)
        #pprint(data)
        #print(data.shape)
        data = data.swapaxes(2,3)  # (0,1,2,3,4) -> (0,1,3,2,4)
        data = data.reshape(self.rgb_size, -1, width_pixels * self.pixel_block_size)  # (3*H*W)
        pprint(data)
        return data

    def get_calibration_img(self, img_file):
        enc_data = self.gen_calibration_data()
        marker_data = self.add_marker_data(enc_data)
        protect_data = self.add_protect_data(marker_data)
        img = self.data_to_img(protect_data)
        img.save(img_file)
        #print('file %s saved!' % img_file)

    def gen_rgb_block(self, blk_type, width, hight):
        assert width > 0 and hight > 0, 'invalid value'
        value = 255
        one_data = np.ones((hight, width)).astype(np.uint8) * value
        zero_data = np.zeros((hight, width)).astype(np.uint8)
        if blk_type == 'R':
            data = np.concatenate((one_data, zero_data, zero_data), axis = 0)
        elif blk_type == 'B':
            data = np.concatenate((zero_data, one_data, zero_data), axis = 0)
        elif blk_type == 'G':
            data = np.concatenate((zero_data, zero_data, one_data), axis = 0)
        else:
            raise 'invalid blk type'
        data = data.reshape(-1, hight, width)
        return data

    def add_data_ctrl_info(self, data, width, data_idx = 0):
        pixels_for_block = 16
        pixels_for_space = 8
        bin_num_for_data_idx = 16
        # 16x16, R - 1, G - 0
        # 16x8, B - space, break
        one_block = self.gen_rgb_block('R', pixels_for_block, pixels_for_block)
        zero_block = self.gen_rgb_block('G', pixels_for_block, pixels_for_block)
        space_block = self.gen_rgb_block('B', pixels_for_space, pixels_for_block)
        width_for_all_blocks = (pixels_for_block + pixels_for_space) * bin_num_for_data_idx
        assert data_idx >= 0 and data_idx < 65536, 'invalid data_idx.'
        assert width > width_for_all_blocks , 'width not enough for 16 bit data index.'
        end_block = self.gen_rgb_block('B', width - width_for_all_blocks, pixels_for_block)

        remainder_list = []
        for i in range(bin_num_for_data_idx):
            remainder = data_idx % 2
            data_idx = int(data_idx/2)
            remainder_list.append(remainder)
        remainder_list.reverse()

        for i in range(bin_num_for_data_idx):
            if i == 0:
                ctrl_data = space_block
            else:
                ctrl_data = np.concatenate((ctrl_data, space_block), axis = 2)
            if remainder_list[i] == 1:
                block = one_block
            else:
                block = zero_block
            ctrl_data = np.concatenate((ctrl_data, block), axis = 2)
        ctrl_data = np.concatenate((ctrl_data, end_block), axis = 2)
        #pprint(ctrl_data)
        #print(ctrl_data.shape, data.shape, width)
        data = np.concatenate((ctrl_data, data), axis=1)
        return data

    @time_evaluate
    def add_marker_data(self, data, data_idx = 0):
        #return data
        # data: (3*H*W)
        data = np.concatenate((self.marker_data_top, data, self.marker_data_bottom), axis=1)
        #pprint(data)
        data = self.add_data_ctrl_info(data, self.pixel_width_height[0] * self.pixel_block_size, data_idx)
        #pprint(data)
        return data

    @time_evaluate
    def add_protect_data(self, data):
        #return data
        # data: (3*H*W)
        # row
        data = np.concatenate((self.protect_data_seq_top, data), axis=1)
        # col
        protect_data = self.protect_data_seq_left  # 3 * H * 4
        #blank_data = np.tile(np.array([0, 0, 0]), self.pixel_block_size).reshape(self.rgb_size, -1, self.pixel_block_size)   # 3 * 1 * 4
        data_height = data.shape[1]
        blank_data_height = data_height - protect_data.shape[1]
        blank_data_width = protect_data.shape[2]
        blank_data = np.zeros((self.rgb_size, blank_data_height, blank_data_width))   # 3 * 1 * 4
        #print(blank_data.shape, protect_data.shape)
        protect_data = np.concatenate((blank_data, protect_data), axis=1)
        #print(protect_data.shape, data.shape)
        protect_data = protect_data.reshape(self.rgb_size, -1, self.pixel_block_size)   # 3 * H * 4
        protect_data = protect_data.astype(np.uint8)
        #print(protect_data.shape, data.shape)
        data = np.concatenate((protect_data, data), axis=2)
        return data

    @time_evaluate
    def set_data_to_img(self, text, img_file, data_idx = 0):
        binary_data = self.string_to_binary(text)
        raw_data = self.gen_data(binary_data)
        enc_data = self.encode_data(raw_data)
        marker_data = self.add_marker_data(enc_data, data_idx)
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

        if ImgUtils.ONLY_CENTER_PIXELS_FOR_DECODE:
            if self.pixel_block_size == 4:
                data = data[:, :, [5,6,9,10]]  # only get the center 4 pixels, for 4x4
            elif self.pixel_block_size == 5:
                data = data[:, :, 12]  # only get the center 4 pixels, for 5x5
            elif self.pixel_block_size == 6:
                data = data[:, :, [14,15,20,21]]  # only get the center 4 pixels, for 6x6
        #print('size:')
        #print(data.shape)
        #pprint(data)
        if np.ndim(data) == 3:
            data = np.round(np.mean(data, 2)).reshape(-1)  # 3*(H*W)
        else:
            data = data.reshape(-1)
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
    def data_parser(self, data_bit, only_header_decode = False):
        # encode(length( 32 bit) + data_payload + md5 (128 bit) + padding) + padding
        assert len(data_bit) == self.raw_data_size, 'data_bit len %d != raw_data_size %d' % (len(data_bit), self.raw_data_size)
        if self.enable_permute: data_bit = self.unpermute(data_bit)
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
            data_size_before_encode = rs_block_num * self.rs_payload_size * 8  # bits
            data_size_after_encode = rs_block_num * self.rs_block_size * 8  # bits
            fake_flag = False
            if rs_block_num > 1:
                #print('rs block num %d' % rs_block_num)
                if only_header_decode:  # if do not decode payload, just fake it
                    #print('only decode header, fake data.')
                    fake_flag = True
                    fake_size = data_size_before_encode - len(block_decode_data)
                    next_block_decode_data = np.zeros(fake_size).astype(np.int32)
                else:
                    next_block_decode_data = self.coder.decode(data_bit[first_block_data_size_after_encode:data_size_after_encode]) # bit
                block_decode_data = np.concatenate((block_decode_data, next_block_decode_data)).astype(np.int32)
            assert len(block_decode_data) == data_size_before_encode, 'block_decode_data len %d != data_size_before_encode %d' % (len(block_decode_data), data_size_before_encode)
            block_decode_data = block_decode_data[:data_size + self.length_size + self.md5_size]
            rx_data_payload = block_decode_data[:-self.md5_size]  # bit
            rx_md5_data = block_decode_data[-self.md5_size:]   # bit
            
            if fake_flag:
                check_pass = True
            else:
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
        marker_seq = self.marker_seq_top
        if marker_seq.size > 500: marker_seq = marker_seq[:500]  # long marker leads to long time to find marker
        #print(self.marker_seq_top.shape, marker_seq.shape)
        data_seq = data[0,:-1,:].reshape(-1) - 128
        # find the marker index by the history result to speed up the search process
        if self.marker_index_found is None:
            #print(data_seq.shape, marker_seq.shape)
            conv = np.convolve(data_seq, np.flipud(marker_seq), 'valid') / marker_seq.size
            conv = conv.astype(np.int32)
            index = np.argmax(conv)
            #print(conv[index-10:index+10])
            #print(conv[0:index+10])
            #pprint(marker_seq[0:20])
            #pprint(data_seq[index:index+20])
            max_conv_value = conv[index]
        else:
            search_range = ImgUtils.SEARCH_MARKER_IN_PIXEL_RANGE * W + self.pixel_block_size
            data_seq = data_seq[self.marker_index_found - search_range:self.marker_index_found + search_range]
            conv = np.convolve(data_seq, np.flipud(marker_seq), 'valid') / marker_seq.size
            conv = conv.astype(np.int32)
            index = np.argmax(conv)
            max_conv_value = conv[index]
            index = index + self.marker_index_found - search_range
        if max_conv_value < 5000: #10000:
            print('do not find top marker.')
            #self.marker_index_found = None
            return None
        else:
            row_index, col_index = divmod(index, W)
            data_block_H = self.pixel_width_height[1]*self.pixel_block_size
            data_block_W = self.pixel_width_height[0]*self.pixel_block_size
            print('row index %d, col index %d, max value %d' % (row_index, col_index, max_conv_value))
            bottom_marker_seq = self.marker_seq_bottom
            #pprint(bottom_marker_seq[:50])
            #top_marker_data = data[0, row_index, col_index:col_index+self.pixel_width_height[0]*self.pixel_block_size].reshape(-1)
            #pprint(top_marker_data[:50])
            bottom_marker_data = data[0,row_index+1+data_block_H, col_index:col_index+data_block_W].reshape(-1) - 128
            #pprint(bottom_marker_data[:50])
            #print(bottom_marker_data.shape, bottom_marker_seq.shape)
            if bottom_marker_data.size != bottom_marker_seq.size: return None
            assert bottom_marker_data.size == bottom_marker_seq.size, 'invalid marker seq size.' 
            
            conv_value = sum(bottom_marker_data * bottom_marker_seq) / bottom_marker_seq.size
            if conv_value < 5000:
                print('the bottom marker do not match!')
                return None
            if not self.marker_index_found is None:
                #print('previous index is %d, current index is %d.' % (self.marker_index_found, index))
                pass
            self.marker_index_found = index
            data = data[:, row_index+1:row_index+1+data_block_H, col_index:col_index+data_block_W]  # do not include top and bottom marker
            #img = self.data_to_img(data)
            #img.show()
            # 3 * H * W, remove marker
            #data = data[:, 1:, :]

            #print('data:\n', data.shape, data[0, 0:10, 0:10])
            return data

    @time_evaluate
    def get_pixel_data_from_screen(self, from_img_file = ''):
        rx_raw_data = self.get_screen(from_img_file)
        rx_data = self.get_data_by_marker(rx_raw_data)
        if rx_data is None: return None
        #print('rx_data:', rx_data.shape)
        return rx_data

    @time_evaluate
    def get_data_from_screen(self, from_img_file = '', to_file = False):
        rx_data = self.get_pixel_data_from_screen(from_img_file)
        if rx_data is None: return ''

        dec_data = self.decode_data(rx_data)
        #print('dec_data:', dec_data.shape)
        only_header_decode = to_file  # if img to file, only decode header
        dec_data_payload = self.data_parser(dec_data, only_header_decode = only_header_decode)
        if dec_data_payload is None: return ''
        #print('dec_data_payload:', dec_data_payload.shape)
        text = self.binary_to_string(dec_data_payload)
        #print('img to text', text)
        return text

    def save_img_to_file(self, rx_img_file):
        self.screen_img.save(rx_img_file)
        #print('screen img saved: ', rx_img_file)

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

    def _screen_to_file(self, img = None, data_idx = None):
        # img_to_file take 2 steps
        # (1) save img to a file
        # (2) if 
        rx_img_file = r'data\rx_data_%d.png' % data_idx
        
    @time_evaluate
    def get_screen(self, from_img_file = ''):
        if from_img_file:
            assert os.path.isfile(from_img_file), 'no file %s found!' % from_img_file
            img = Image.open(from_img_file)
        else:
            img = pyautogui.screenshot()
            if ImgUtils.SAVE_SCREEN_TO_FILE:
                now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = 'data/screen_%s.png' % now_str
                img.save(filename)
                print('img saved: ', filename)
                #img = Image.open('data/screen_20220501_180007.png')
        self.screen_img = img
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
    elif option == 3:
        #data = img_utils.get_screen()
        data = img_utils.get_data_from_screen('data/screen_20220504_102051.png')
        print('test get screen, data:\n', data)
    elif option == 4:
        img_utils = ImgUtils(pixel_width = 16*16, pixel_hight = 16*7, pixel_block_size = 16)
        img_utils.get_calibration_img('data/calibration.png')
    else:
        raw_data = img_utils.get_data()
        raw_data = img_utils.gen_data(raw_data)
        enc_data = img_utils.encode_data(raw_data)
        marker_data = img_utils.add_marker_data(enc_data)

        rx_raw_data = img_utils.get_screen()
        rx_data = img_utils.get_data_by_marker(rx_raw_data)
        if not rx_data is None:
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

