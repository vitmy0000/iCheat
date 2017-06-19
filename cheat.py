import argparse
import curses
from curses.textpad import Textbox
import fcntl
import sys
import os
import termios

parser = argparse.ArgumentParser(description="Cheat Sheep Terminal Application")
parser.add_argument('-s', '--sheet', help="cheat sheet file", required=True)
args = parser.parse_args()

class InputWindow:
    def __init__(self):
        self.window = curses.newwin(1, 100, 0, 2)
        self.string = ''

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
    def __init__(self):
        self.window = curses.newwin(50, 100, 1, 0)

    def show(self, target_items):
        self.window.erase()
        for i, target_item in enumerate(target_items):
            self.window.addstr(i, 0, target_item)
        self.window.refresh()

class SearchEngine:
    def __init__(self, sheet):
        self.items = self.parse(sheet)

    def parse(self, sheet):
        items = []
        with open(sheet) as f:
            for line in f:
                item = line.strip()
                if item != '':
                    items.append(item)
        return items

    def query(self, query_string):
        query_items = query_string.split()
        target_items = []
        for target_item in self.items:
            flag = True
            for query_item in query_items:
                if target_item.find(query_item) == -1:
                    flag = False
            if flag:
                target_items.append(target_item)
        return target_items

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
    stdscr.addch(0, 0, '>')
    stdscr.addch(0, 1, ' ')
    search_engine = SearchEngine(args.sheet)
    display_window = DisplayWindow()
    input_window = InputWindow()

    # key_code = stdscr.getkey()
    # return str(ord(key_code))

    while True:
        key_code = stdscr.getkey()
        if ord(key_code) == 27: # esc
            return 'esc'
        elif ord(key_code) == 10: # enter
            return input_window.string
        else:
            display_window.show(
                search_engine.query(
                    input_window.process_key(key_code)))
            input_window.refresh()

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
