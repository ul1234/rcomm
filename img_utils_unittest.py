#!/usr/bin/python
# -*- coding: utf-8 -*-

from img_utils import ImgUtils
import subprocess
import unittest, time
import numpy as np
from pprint import pprint

#class ImgUtilsTest(unittest.TestCase):
class ImgUtilsTest():
    def setUp(self):
        self.img_utils = ImgUtils(pixel_width = 1200, pixel_hight = 480, pixel_block_size = 32)
        self.max_tx_bytes = self.img_utils.get_max_text_size()
        print('max tx bytes: %d' % self.max_tx_bytes)
        self.temp_tx_img_file = 'unittest.png'
        self.init_startupinfo()

    def tearDown(self):
        self.img_utils = None

    def init_startupinfo(self):
        STARTF_USESHOWWINDOW = 1
        SW_MAXIMIZE = 3
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_MAXIMIZE
        self.startupinfo = startupinfo

    def _test_with_img_file(self, input_text):
        self.img_utils.set_data_to_img(input_text, self.temp_tx_img_file)
        output_text = self.img_utils.get_data_from_screen(self.temp_tx_img_file)
        self.assertEqual(input_text, output_text)

    def test_short_seq(self):
        input_text = 'abcdefghijklmn'
        self._test_with_img_file(input_text)

    def test_long_seq(self):
        input_text = 'abcdefghijklmn' * 1000
        self._test_with_img_file(input_text)

    def _test_with_screen(self, input_text):
        self.img_utils.set_data_to_img(input_text, self.temp_tx_img_file)
        img_viewer = subprocess.Popen(['mspaint', self.temp_tx_img_file], startupinfo = self.startupinfo)
        time.sleep(1)
        output_text = self.img_utils.get_data_from_screen()
        img_viewer.terminate()
        img_viewer.wait()
        self.assertEqual(input_text, output_text)

    def test_short_seq_screen(self):
        input_text = 'abcdefghijklmn'
        self._test_with_screen(input_text)

    def test_long_seq_screen(self):
        input_text = 'abcdefghijklmn' * 1000
        self._test_with_screen(input_text)

    def test_permute(self):
        data_size = self.img_utils.raw_data_size
        data = np.array(range(data_size), dtype=np.int32)
        permute_data = self.img_utils.permute(data)
        #print(permute_data)
        unpermute_data = self.img_utils.unpermute(permute_data)
        #print(unpermute_data)
        self.assertEqual(list(data), list(unpermute_data))

class ImgUtilsCalibrationTest(unittest.TestCase):
    def setUp(self):
        self.img_utils = ImgUtils(pixel_width = 16*16, pixel_hight = 16*7, pixel_block_size = 16)
        self.max_tx_bytes = self.img_utils.get_max_text_size()
        print('max tx bytes: %d' % self.max_tx_bytes)
        self.temp_tx_img_file = 'calibration.png'
        self.init_startupinfo()

    def tearDown(self):
        self.img_utils = None

    def init_startupinfo(self):
        STARTF_USESHOWWINDOW = 1
        SW_MAXIMIZE = 3
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = SW_MAXIMIZE
        self.startupinfo = startupinfo

    def test_calibration(self):
        time.sleep(2)
        #gen_data = True
        gen_data = False
        if gen_data:
            self.img_utils.get_calibration_img(self.temp_tx_img_file)
            img_viewer = subprocess.Popen(['mspaint', self.temp_tx_img_file], startupinfo = self.startupinfo)
            time.sleep(1)
        pixel_data = self.img_utils.get_pixel_data_from_screen()
        #pixel_data = self.img_utils.get_pixel_data_from_screen('data/screen_20220504_094034.png')
        if gen_data:
            img_viewer.terminate()
            img_viewer.wait()
        pprint(pixel_data)
        if not pixel_data is None:
            # pixel_data: 3*H*W
            data = pixel_data.swapaxes(0,1)  # change to H * 3 * W
            print(data.shape)
            width = data.shape[2]
            data = data.reshape(-1)
            with open('data/calibration.txt', 'w') as f:
                index = 0
                for j in range(int(data.size / width)):
                    for i in range(width):
                        f.write('%d ' % data[index])
                        index += 1
                    f.write('\n')
        # get screen multiple times
        #while True:
        #    time.sleep(2)
        #    self.img_utils.get_pixel_data_from_screen()


if __name__ == "__main__":
    unittest.main(verbosity = 2)
