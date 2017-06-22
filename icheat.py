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

    def build_window(self, stdscr):
        height, width = stdscr.getmaxyx()
        if width < 5 or height < 1:
            return None
        stdscr.addch(0, 0, '>')
        stdscr.addch(0, 1, ' ')
        return curses.newwin(1, width, 0, 2)

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

class DisplayWindow:
    def __init__(self, stdscr, provider):
        self.window = self.build_window(stdscr)
        self.provider = provider
        self.display_item_info = {}
        self.highlight_index = 0

    def build_window(self, stdscr):
        height, width = stdscr.getmaxyx()
        if height < 2:
            return None
        return curses.newwin(height, width, 1, 0)

    def display_item(self, item, line_num):
        """return consumed line cnt"""
        item_index = len(self.display_item_info)
        self.display_item_info[item_index] = {}
        self.display_item_info[item_index]['line_nums'] = []
        self.display_item_info[item_index]['contents'] = []
        for content in item:
            self.display_item_info[item_index]['line_nums'].append((line_num))
            self.display_item_info[item_index]['contents'].append((content))
            self.window.addstr(line_num, 0, content[:50])
            line_num += 1
        return line_num

    def highlight(self):
        if len(self.display_item_info) == 0:
            return
        item_info = self.display_item_info[self.highlight_index]
        for line, content in zip(item_info['line_nums'], item_info['contents']):
            self.window.addstr(line, 0, content[:50], curses.A_STANDOUT)
        self.window.refresh()

    def show(self):
        '''display items and highlights

        This method is called on input text change
        '''
        self.display_item_info = {}
        self.window.erase()
        line_limit = self.window.getmaxyx()[0]
        line_num = 0
        while line_num <= 10:# line_limit:
            try:
                item = self.provider.provide()
            except StopIteration:
                break
            line_num = self.display_item(item, line_num)
        self.highlight()
        self.window.refresh()

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
    stdscr.notimeout(0)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    return stdscr

def run(stdscr):
    stdscr.clear()
    provider = Provider.create_provider(args)
    input_window = InputWindow(stdscr)
    display_window = DisplayWindow(stdscr, provider)
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
        elif key_code == 'KEY_DOWN' or key_code == 'KEY_UP':
            # display_window.process_key(key_code)
            pass
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
