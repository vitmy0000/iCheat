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

class InputBox:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.string = ''

    def get_str_cursor_index(self):
        return curses.getsyx()[1] - 2

    def insert_char(self, key_code):
        insert_index = self.get_str_cursor_index()
        self.string = self.string[:insert_index] \
            + key_code + self.string[insert_index:]
        self.refresh()

    def refresh(self):
        self.stdscr.addstr(0, 2, ' ' * 10)
        self.stdscr.addstr(0, 2, self.string)

    def delete_char(self):
        delete_index = self.get_str_cursor_index()
        self.string = self.string[:delete_index - 1] \
            + self.string[delete_index:]
        curses.setsyx(0, curses.getsyx()[1] - 1)
        self.refresh()

    def process_key(self, key_code):
        if 32 <= ord(key_code) <= 126:
            self.insert_char(key_code)
        elif ord(key_code) == 127: # delete
            self.delete_char()

class DisplayBox:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.stdscr.clear()
        self.stdscr.addch(0, 0, '>')
        self.stdscr.addch(0, 1, ' ')
        self.stdscr.refresh()

def init():
    os.environ.setdefault('ESCDELAY', '25')
    stdscr = curses.initscr()
    stdscr.notimeout(0)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    return stdscr

def run(stdscr):
    display_box = DisplayBox(stdscr)
    input_box = InputBox(stdscr)

    # key_code = stdscr.getkey()
    # return str(ord(key_code))

    while True:
        key_code = stdscr.getkey()
        if ord(key_code) == 27: # esc
            return 'esc'
        elif ord(key_code) == 10: # enter
            return input_box.string
        else:
            input_box.process_key(key_code)

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
