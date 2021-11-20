#!/usr/bin/python
# -*- coding: utf-8 -*-

from img_utils import ImgUtils
import subprocess
import unittest, time
import numpy as np

class ImgUtilsTest(unittest.TestCase):
    def setUp(self):
        self.img_utils = ImgUtils()
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


if __name__ == "__main__":
    unittest.main(verbosity = 2)
