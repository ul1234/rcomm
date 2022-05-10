#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
import os, sys, time
import zipfile, base64
from filetool import FileTool
from decorator import thread_func, time_evaluate

class MyException(Exception): pass

class ZipUtil:
    @staticmethod
    def zip(src_files, zip_file, base_path = None):
        filelist = []
        for src_file in src_files:
            if not os.path.exists(src_file): raise Exception('%s not exists.' % src_file)
            if os.path.isfile(src_file):
                filelist.append(src_file)
            else:
                for root, dirs, files in os.walk(src_file):
                    for name in files:
                        filelist.append(os.path.join(root, name))

        zf = zipfile.ZipFile(zip_file, "w", zipfile.zlib.DEFLATED)
        if not base_path:
            if len(src_files) == 1:
                base_path = os.path.dirname(src_files[0])
            else:
                base_path = os.path.dirname(os.path.commonprefix([p + os.path.sep if os.path.isdir(p) else p for p in src_files]))
        for file in filelist:
            zf.write(file, os.path.relpath(file, base_path))
        zf.close()

    @staticmethod
    def unzip(zip_file, dest_dir):
        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
        zfobj = zipfile.ZipFile(zip_file)
        for name in zfobj.namelist():
            name = name.replace('\\','/')
            if name.endswith('/'):
                os.makedirs(os.path.join(dest_dir, name))
            else:
                ext_filename = os.path.join(dest_dir, name)
                ext_dir = os.path.dirname(ext_filename)
                if not os.path.exists(ext_dir) : os.makedirs(ext_dir)
                with open(ext_filename, 'wb') as f:
                    f.write(zfobj.read(name))

    @staticmethod
    def b64enc(src_file, dest_file):
        with open(src_file, 'rb') as src:
            with open(dest_file, 'wb') as dest:
                # encode() inserts a newline character (b'\n') after every 76 bytes of the output, as well as ensuring that the output always ends with a newline
                # https://docs.python.org/3/library/base64.html
                base64.encode(src, dest)

    @staticmethod
    def b64dec(src_file, dest_file):
        with open(src_file, 'rb') as src:
            with open(dest_file, 'wb') as dest:
                base64.decode(src, dest)

class RComm:
    def __init__(self, log_to_file = True):
        self.server_prefix, self.server_postfix = '<s>', '</s>'
        self.client_prefix, self.client_postfix = '<c>', '</c>'
        self.delimiter = '<p>\r\n'
        self.file_path = os.path.dirname(os.path.abspath(__file__))
        self.trans_path = os.path.join(self.file_path, 'trans')
        self.send_cmds_list = ['INFO', 'QUERY', 'FILE', 'PACKET']
        self.receive_cmds_list = ['WAIT', 'NEED', 'OK', 'FINISH']
        self.log_file = os.path.join(self.trans_path, 'temp_log.txt')
        self.tx_zip_file = os.path.join(self.trans_path, 'tx_temp.zip')
        self.rx_zip_file = os.path.join(self.trans_path, 'rx_temp.zip')
        self.tx_b64_file, self.rx_b64_file = '_tx_temp.txt', '_rx_temp.txt'
        if not os.path.isdir(self.trans_path): os.makedirs(self.trans_path)
        self.filetool = FileTool()
        self.send_cmd_num = 0
        self.rcv_cmd_num = 0
        self.log_to_file = log_to_file

    def init_tx_rx(self):
        self.tx_text = self.tx_comm_tool.set_text
        self.tx_reset_text = self.tx_comm_tool.reset_text
        self.tx_empty_text = self.tx_comm_tool.empty_text
        self.rx_text = self.rx_comm_tool.get_text
        self.clear_rx_text = self.rx_comm_tool.clear_get_text
        self.max_tx_bytes = self.tx_comm_tool.get_max_tx_text_size()

    def close_comm(self):
        self.tx_comm_tool.close()
        self.rx_comm_tool.close()

    @time_evaluate
    def _receive_wait(self, timeout = 0):
        def _fake_payload(text):
            add_post_fix = self.delimiter + self.rx_postfix
            post_fix_len = len(add_post_fix)
            text = text[:-post_fix_len] + add_post_fix
            return text

        total_times = timeout*2 if timeout else 1000000
        for times in range(total_times):
            time.sleep(0.5)
            text = self.rx_text(expect_data_idx = self.rcv_cmd_num, fake_func = _fake_payload)
            #print('receive text: %s' % text)
            cmd, payload = self._unpack(text)
            if cmd:
                self.print_debug('receive cmd: %s' % cmd)
                return (cmd, payload)
        raise MyException('%ss timeout, no valid cmd received!' % timeout)

    def print_debug(self, text):
        if not self.log_to_file:
            self.print_(text)
        else:
            if not hasattr(self, 'init_log_file'):
                self.init_log_file = True
                open(self.log_file, 'w').close()
            with open(self.log_file, 'a') as f:
                f.write('[%s]%s\n' % (datetime.now().strftime('%I:%M:%S'), text))

    def print_(self, text):
        #print(text)
        print('[%s]%s' % (datetime.now().strftime('%I:%M:%S'), text))

    def print_transfer(self, total_bytes, transfer_bytes):
        def _print_transfer(total_bytes, transfer_bytes):
            # [#####          ] 23% TimeElapse: 00:01:20
            total_symbol_num = 20  # '#' number
            symbol_num = transfer_bytes * total_symbol_num / total_bytes
            percentage = transfer_bytes * 100 / total_bytes
            time_elapse = str(datetime.now() - self.start_transfer_time).split('.')[0]
            status = '[%s%s] %3d%% SendNum: %d TimeElapse: %s' % ('#'*int(symbol_num), ' '*int(total_symbol_num - symbol_num), percentage, self.send_cmd_num, time_elapse)
            sys.stdout.write('\r' + status)
            sys.stdout.flush()
        if not hasattr(self, 'start_transfer_time'): self.start_transfer_time = datetime.now()
        if hasattr(self, 'total_bytes') and hasattr(self, 'transfer_bytes'):
            if total_bytes == self.total_bytes and transfer_bytes != self.transfer_bytes:
                _print_transfer(total_bytes, transfer_bytes)
                if transfer_bytes == total_bytes: print('\n')
        self.total_bytes, self.transfer_bytes = total_bytes, transfer_bytes

    def _unpack(self, text):
        if text and text.startswith(self.rx_prefix):
            text_split = text.split(self.delimiter)
            if text_split[-1].strip() == self.rx_postfix:
                cmd = text_split[0][len(self.rx_prefix):].strip()
                payload = text_split[1] if len(text_split) > 2 else None
                if payload:
                    payload = payload.replace('\r', '')  # every '\n' will come up with a 'r', so delete it
                    #print('rx payload len: %d' % len(payload))
                    #print(payload)
                return (cmd, payload)
        return (None, None)

    def send_cmd(self, cmd, payload = None):
        text = self.tx_prefix + cmd + self.delimiter
        if payload: text += payload + self.delimiter
        #if payload:
            #print('tx payload len: %d' % len(payload))
            #print(payload)
        text += self.tx_postfix
        self.clear_rx_text()
        self.tx_text(text, data_idx = self.send_cmd_num)
        self.cmd_text_for_resend = (cmd, text)
        self.print_debug('send cmd: %s' % cmd)
        self.send_cmd_num = self.send_cmd_num + 1

    def expect_cmd(self, cmd):
        def _cmd_to_text(cmd):
            text = self.rx_prefix + cmd + self.delimiter
            text += self.rx_postfix
            return text
        #print('expect text: %s' % cmd)
        self.rx_comm_tool.expect_text(cmd, cmd_to_text_func = _cmd_to_text)
        
    def _resend_cmd(self):
        self.tx_reset_text()
        time.sleep(0.3)
        self.tx_text(self.cmd_text_for_resend[1], data_idx = self.send_cmd_num)
        self.print_debug('resend cmd: %s' % self.cmd_text_for_resend[0])
        
    def _wait_for_cmd(self, state, wait_cmd, timeout = 0):
        start_time = time.time()
        is_send_cmd = True if wait_cmd in self.receive_cmds_list else False
        while True:
            try:
                rx_cmd = ''
                cmd, payload = self._receive_wait()
                rx_cmd = cmd.split()[0]
                if rx_cmd != wait_cmd: raise MyException('state %s, wait: %s, received: %s' % (state, wait_cmd, cmd))

                if is_send_cmd:    # send
                    if wait_cmd == 'NEED':
                        files_num = int(cmd.split()[1])
                        files_list = self.filetool.string_to_object(payload) if files_num else []
                        if files_num != len(files_list): raise MyException('state %s received: %s, files_num %d != len(files) %d.' % (state, cmd, files_num, len(files_list)))
                        return files_list
                    else: # 'WAIT', 'OK', 'FINISH'
                        rx_bytes = int(cmd.split()[1])
                        return rx_bytes
                else:  # receive
                    if wait_cmd == 'INFO':
                        info_len = int(cmd.split()[1])
                        if len(payload) != info_len: raise MyException('state %s received: %s, info len %d, payload len: %d' % (state, cmd, info_len, len(payload)))
                        return self.filetool.string_to_object(payload)
                    elif wait_cmd == 'QUERY':
                        rx_bytes = int(cmd.split()[1])
                        return rx_bytes
                    elif wait_cmd == 'FILE':
                        magic, file_len = cmd.split()[1:]
                        return (magic, int(file_len))
                    else:  # 'PACKET'
                        start_bytes, tx_len = map(int, cmd.split()[1:])
                        if len(payload) != tx_len: raise MyException('state %s received: %s, tx_len %d, payload len: %d' % (state, cmd, tx_len, len(payload)))
                        return (start_bytes, tx_len, payload)
            except MyException as e:
                self.print_debug(e)
                if timeout and (time.time() - start_time > timeout): return None
                if is_send_cmd:
                    self._resend_cmd()
                elif wait_cmd == 'FILE' and rx_cmd == 'QUERY':
                    self._resend_cmd()

    def enc_file(self, src_files, magic = '000', cont_mode = False, base_path = None):
        tx_b64_file = os.path.join(self.trans_path, magic + self.tx_b64_file)
        if os.path.isfile(tx_b64_file) and not cont_mode: os.remove(tx_b64_file)
        if not os.path.isfile(tx_b64_file):
            self.print_('start compress and encode files...')
            ZipUtil.zip(src_files, self.tx_zip_file, base_path = base_path)
            ZipUtil.b64enc(self.tx_zip_file, tx_b64_file)
            if os.path.exists(self.tx_zip_file): os.remove(self.tx_zip_file)
        return tx_b64_file

    def send_file_info(self, tx_folder):
        TX_FILE_INFO = 3
        TX_WAIT = 4
        self.print_('start generate info for %s...' % tx_folder)
        folder_info = self.filetool.object_to_string(self.filetool.gen_folder_info(tx_folder))
        self.print_('start sending folder info...')
        self.send_cmd('INFO %d' % len(folder_info), folder_info)
        rx_length = self._wait_for_cmd(TX_FILE_INFO, 'WAIT')
        self.print_('wait for client process...')
        self.send_cmd('QUERY %d' % rx_length)
        need_files = self._wait_for_cmd(TX_WAIT, 'NEED')
        self.print_('client need %d files' % len(need_files))
        if need_files:
            filename = self.enc_file([os.path.join(tx_folder, f) for f in need_files], base_path = tx_folder)
        else:
            filename = ''
        return filename

    def send_file(self, filename):
        TX_FILE_HEAD_STATE = 0
        TX_STATE = 1
        TX_END_STATE = 2

        state = TX_FILE_HEAD_STATE
        size = os.path.getsize(filename)
        with open(filename, 'rb') as f:
            while True:
                if state == TX_FILE_HEAD_STATE:
                    self.send_cmd('FILE %s %d' % (os.path.basename(filename)[:3], size))  # magic: filename[:3]
                    self.expect_cmd('OK 0')
                    state = TX_STATE
                elif state == TX_STATE:
                    rx_bytes = self._wait_for_cmd(state, 'OK')
                    remain_bytes = size - rx_bytes
                    if remain_bytes <= self.max_tx_bytes:
                        tx_len = remain_bytes
                        state = TX_END_STATE  # the last packet
                        self.expect_cmd('FINISH %d' % (rx_bytes + tx_len))
                    else:
                        tx_len = self.max_tx_bytes
                        self.expect_cmd('OK %d' % (rx_bytes + tx_len))
                    self.print_transfer(size, rx_bytes)
                    f.seek(rx_bytes)
                    self.send_cmd('PACKET %d %d' % (rx_bytes, tx_len), f.read(tx_len).decode())
                elif state == TX_END_STATE:
                    rx_bytes = self._wait_for_cmd(state, 'FINISH')
                    self.print_transfer(size, rx_bytes)
                    break
        if os.path.exists(filename): os.remove(filename)
        self.print_('send file %s finished.' % filename)
        self.close_comm()

    def receive_file_info(self, ref_folder, dest_folder):
        RX_FILE_INFO_STATE = 3
        self.tx_reset_text()
        folder_info = self._wait_for_cmd(RX_FILE_INFO_STATE, 'INFO')
        self.send_cmd('WAIT %d' % len(folder_info))
        self.print_('start to process folder info...')
        remain_files = self.filetool.copy_folder_with_info(folder_info, ref_folder, dest_folder)
        self.print_('process folder info finished.')
        self.tx_reset_text()
        self._wait_for_cmd(RX_FILE_INFO_STATE, 'QUERY')
        self.send_cmd('NEED %d' % len(remain_files), self.filetool.object_to_string(remain_files) if remain_files else None)
        return remain_files

    def receive_file(self, cont_mode = False):
        RX_FILE_HEAD_STATE = 0
        RX_STATE = 1
        RX_END_STATE = 2

        state = RX_FILE_HEAD_STATE
        while True:
            if state == RX_FILE_HEAD_STATE:
                self.tx_reset_text()
                magic, file_len = self._wait_for_cmd(state, 'FILE')
                rx_b64_file = os.path.join(self.trans_path, magic + self.rx_b64_file)
                if os.path.isfile(rx_b64_file) and not cont_mode: os.remove(rx_b64_file)
                if os.path.isfile(rx_b64_file):
                    rx_bytes = os.path.getsize(rx_b64_file)
                    f = open(rx_b64_file, 'ab')  # append
                else:
                    rx_bytes = 0
                    f = open(rx_b64_file, 'wb')
                state = RX_STATE
                self.rcv_cmd_num += 1  # update received cmd number
            elif state == RX_STATE:
                self.send_cmd('OK %d' % (rx_bytes))
                start_bytes, tx_len, payload = self._wait_for_cmd(state, 'PACKET')
                if start_bytes == rx_bytes:
                    f.write(payload.encode())
                    rx_bytes += tx_len
                    self.rcv_cmd_num += 1  # update received cmd number
                else:
                    self.print_debug('received start_bytes %d != rx bytes %d.' % (start_bytes, rx_bytes))
                self.print_transfer(file_len, rx_bytes)
                if rx_bytes == file_len: state = RX_END_STATE
            elif state == RX_END_STATE:
                #for try_times in range(6):
                #    self.send_cmd('FINISH %d' % (rx_bytes))
                #    result = self._wait_for_cmd(state, 'PACKET', timeout = 10)
                #    if not result: break  # timeout
                self.send_cmd('FINISH %d' % (rx_bytes))
                self.rcv_cmd_num += 1  # update received cmd number
                break
        if f: f.close()
        #self.tx_empty_text()
        self.close_comm()
        return rx_b64_file

    def dec_file(self, filename, dest_dir = ''):
        if not dest_dir: dest_dir = self.trans_path
        if not os.path.isdir(dest_dir): os.makedirs(dest_dir)
        ZipUtil.b64dec(filename, self.rx_zip_file)
        ZipUtil.unzip(self.rx_zip_file, dest_dir)
        if os.path.exists(filename): os.remove(filename)
        #if os.path.exists(self.rx_zip_file): os.remove(self.rx_zip_file)
        self.print_('received to %s finished.' % dest_dir)

if __name__ == '__main__':
    test = 0  # 0
    if test == 1:
        #ZipUtil.b64enc(sys.argv[1], 'test.txt')
        #ZipUtil.b64dec('test.txt', '1.zip')
        ZipUtil.b64dec(sys.argv[1], '1.zip')
        print('done')
    elif test == 2:
        ZipUtil.zip(['32674'], 'temp.zip')
        import bz2
        f = bz2.BZ2File("temp.bz2", "wb", compresslevel=5)
        f.write(open('temp.zip','rb').read())
        f.close()

