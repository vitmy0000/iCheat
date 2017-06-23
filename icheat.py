import argparse
import curses
import fcntl
import sys
import os
import termios

parser = argparse.ArgumentParser(description="Cheat Sheep Terminal Application")
parser.add_argument('-s', '--sheet', help="cheat sheet file", required=True)
args = parser.parse_args()

class InputWindow:
    def __init__(self, stdscr):
        self.string = ''
        self.window = self.build_window(stdscr)
        self.refresh()
        self.funckey_2_action = {
        }

    def get_funckey_2_action(self):
        return self.funckey_2_action

    def build_window(self, stdscr):
        height, width = stdscr.getmaxyx()
        if width < 5 or height < 1:
            return None
        stdscr.addch(0, 0, '>')
        stdscr.addch(0, 1, ' ')
        newwin = curses.newwin(1, width, 0, 2)
        stdscr.refresh()
        return newwin

    def get_str_cursor_index(self):
        return curses.getsyx()[1] - 2

    def insert_char(self, key_code):
        insert_index = self.get_str_cursor_index()
        self.string = self.string[:insert_index] \
            + key_code + self.string[insert_index:]

    def refresh(self):
        self.window.erase()
        self.window.addstr(0, 0, self.string)
        self.window.refresh()

    def delete_char(self):
        delete_index = self.get_str_cursor_index()
        self.string = self.string[:delete_index - 1] \
            + self.string[delete_index:]
        curses.setsyx(0, curses.getsyx()[1] - 1)

    def process_key(self, key_code):
        if 32 <= ord(key_code) <= 126: # normal char
            self.insert_char(key_code)
            return self.string
        elif ord(key_code) == 127: # delete
            self.delete_char()
            return self.string

class DisplayLineInfo:
    """line info for display help

    One item may span multiple display lines
    """
    def __init__(self, line_num, content, item_index):
        self.line_num = line_num
        self.content = content
        self.item_index = item_index

class DisplayWindow:
    def __init__(self, stdscr, provider):
        self.window = self.build_window(stdscr)
        self.provider = provider
        self.funckey_2_action = {
            'KEY_UP': self.highlight_prev,
            'KEY_DOWN': self.highlight_next,
        }
        # display related
        self.cached_item_cnt = 0
        self.cached_line_infos = []
        self.highlighting_item_index = 0
        self.highlighting_line_nums = []
        self.display_offset = 0

    def highlight_prev(self):
        if self.highlighting_item_index == 0:
            return
        self.highlighting_item_index -= 1
        lnum = self.highlighting_line_nums[0] - 1
        self.highlighting_line_nums = []
        while lnum >= 0:
            if (self.cached_line_infos[lnum].item_index
                    == self.highlighting_item_index):
                self.highlighting_line_nums.append(lnum)
                lnum -= 1
            else:
                break
        self.display_offset = min(self.display_offset,
                                  self.highlighting_line_nums[0])
        self.draw()

    def highlight_next(self):
        """may involve new item fetch or redraw"""
        self.highlighting_item_index += 1
        if self.highlighting_item_index == self.cached_item_cnt:
            """fetch next item and it should be highlighted"""
            try:
                item = self.provider.provide()
                self.highlighting_line_nums = []
                self.cache_item(item)
            except StopIteration:
                return
        else:
            lnum = self.highlighting_line_nums[-1] + 1
            self.highlighting_line_nums = []
            while lnum < len(self.cached_line_infos):
                if (self.cached_line_infos[lnum].item_index
                        == self.highlighting_item_index):
                    self.highlighting_line_nums.append(lnum)
                    lnum += 1
                else:
                    break
        # align display box and highlighting item
        window_height = self.window.getmaxyx()[0]
        self.display_offset = max(
            self.display_offset,
            self.highlighting_line_nums[-1] - window_height + 1)
        self.draw()


    def build_window(self, stdscr):
        height, width = stdscr.getmaxyx()
        if height < 2:
            return None
        newwin = curses.newwin(height - 1, width, 1, 0)
        stdscr.refresh()
        return newwin

    def cache_item(self, item):
        for line in item:
            line_num = len(self.cached_line_infos)
            line_info = DisplayLineInfo(line_num, line,
                                        self.cached_item_cnt)
            if (self.cached_item_cnt == self.highlighting_item_index):
                self.highlighting_line_nums.append(line_num)
            self.cached_line_infos.append(line_info)
        self.cached_item_cnt += 1

    def draw(self):
        display_height, display_width = self.window.getmaxyx()
        for line_info in (self.cached_line_infos[
                self.display_offset:self.display_offset + display_height]):
            # clear line first in case of residue display
            self.window.addstr(line_info.line_num - self.display_offset, 0,
                               ' ' * (display_width - 1))
            if line_info.item_index == self.highlighting_item_index:
                self.window.addstr(line_info.line_num - self.display_offset, 0,
                                   line_info.content[:50], curses.A_STANDOUT)
            else:
                self.window.addstr(line_info.line_num - self.display_offset, 0,
                                   line_info.content[:50])
        self.window.refresh()

    def show(self):
        '''display items and highlights

        This method is called on input text change
        '''
        self.window.erase()
        self.cached_item_cnt = 0
        self.cached_line_infos = []
        self.highlighting_item_index = 0
        self.highlighting_line_nums = []
        line_limit = self.window.getmaxyx()[0]
        while len(self.cached_line_infos) < line_limit:
            try:
                item = self.provider.provide()
            except StopIteration:
                break
            self.cache_item(item)
        self.draw()

class Provider:
    @staticmethod
    def create_provider(args):
        provider_type = 'history'
        data_files = [args.sheet]
        if provider_type == 'history':
            return HistoryProvider(data_files)
        elif provider_type == 'cheat':
            return None #CheatProvider(data_files)
        else:
            return None

    def __init__(self, data_files):
        self.items = self.parse(data_files)
        self.item_iterator = iter(self.items)
        self.query_string = ''

    def parse(self, data_files):
        return []

    def reset(self, query_string):
        """on query string change, use new iterator"""
        self.item_iterator = iter(self.items)
        self.query_string = query_string

    def validate(self, target_item):
        pass

    def provide(self):
        """provide one valid item"""
        try:
            while True:
                target_item = self.item_iterator.next()
                if self.validate(target_item):
                    return target_item
        except StopIteration:
            raise

class HistoryProvider(Provider):
    """Provider for command history files

    Each item should be a list of one single line string
    """
    def parse(self, data_files):
        """duplicate item should be remove"""
        items = set()
        for data_file in data_files:
            with open(data_file) as f:
                for line in f:
                    item = line.strip()
                    if item != '':
                        items.add(item)
        return [[x] for x in items]

    def validate(self, target_item):
        query_items = self.query_string.split()
        flag = True
        for query_item in query_items:
            if '\n'.join(target_item).find(query_item) == -1:
                flag = False
        return flag

def init():
    os.environ.setdefault('ESCDELAY', '25')
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    return stdscr

def run(stdscr):
    stdscr.clear()
    provider = Provider.create_provider(args)
    display_window = DisplayWindow(stdscr, provider)
    input_window = InputWindow(stdscr)
    display_window.show()
    input_window.refresh()

    # key_code = stdscr.getkey()
    # return str(ord(key_code))

    while True:
        key_code = stdscr.getkey()
        if len(key_code) == 1 and ord(key_code) == 27: # esc
            return ''
        elif len(key_code) == 1 and ord(key_code) == 10: # enter
            return "enter" #display_window.get_highlight()
        elif key_code in display_window.funckey_2_action:
            display_window.funckey_2_action[key_code]()
        elif key_code == '' or key_code == '':
            input_window.process_key(key_code)
        else:
            # on input text change
            provider.reset(input_window.process_key(key_code))
            display_window.show()
        input_window.refresh() # bring cursor back

def destroy(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()

def inject_terminal_input(str):
    for c in str:
        fcntl.ioctl(sys.stdin, termios.TIOCSTI, c)

if __name__ == '__main__':
    stdscr = init()
    cmd_str = run(stdscr)
    destroy(stdscr)
    inject_terminal_input(cmd_str)

    # curses.wrapper(run)
