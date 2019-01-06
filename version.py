#!/usr/bin/env python3
from enum import Enum


class Digit:
    class Range(Enum):
        Any = 0
        Number = 1
        Range = 2

    def __init__(self, digit_string):
        self.number = None

        if digit_string == '*':
            self.range = Digit.Range.Any
        else:
            self.range = Digit.Range.Range
            self.op = "".join([c for c in digit_string if c not in '0123456789'])
            self.number = int(digit_string[len(self.op):])
            if not self.op:
                self.range = Digit.Range.Number
                self.op = "=="

    def __str__(self):
        if self.range == Digit.Range.Any:
            return '*'
        elif self.range == Digit.Range.Number:
            return str(self.number)
        return self.op + str(self.number)

    def __eq__(self, other):
        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return "TrueBreak"

        if self.range == Digit.Range.Number and other.range == Digit.Range.Number:
            return eval("%i%s%i" % (self.number, self.op, other.number))

        res = True

        if self.op and self.range == Digit.Range.Range:
            res = res and eval("%i%s%i" % (other.number, self.op, self.number))

        if other.op and other.range == Digit.Range.Range:
            res = res and eval("%i%s%i" % (self.number, other.op, other.number))

        return res

    def __lt__(self, other):
        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return True
        return self.number < other.number

    def increase(self):
        self.number += 1


class Version:
    def __init__(self, version_string='*.*.*'):
        self.digits = []
        digits = version_string.split('.')
        nof_digits = len(digits)
        if not nof_digits:
            self.digits.append(Digit(version_string))
        else:
            for digit in digits:
                self.digits.append(Digit(digit))
        while len(self.digits) < 3:
            self.digits.append(Digit('*'))

    def __str__(self):
        ret = []
        for digit in self.digits:
            ret.append(str(digit))
            if digit.range == Digit.Range.Any:
                break
        return ".".join(ret)

    def __eq__(self, other):
        for digit in range(len(self.digits)):
            m = self.digits[digit] == other.digits[digit]
            if m == "TrueBreak":
                return True
            if not m:
                return False
        return True

    def __lt__(self, other):
        loops = len(self.digits) - 1

        while loops > 0:
            if self.digits[loops] < other.digits[loops]:
                return True
            if self.digits[loops] > other.digits[loops]:
                return False
            loops -= 1

        return self.digits[0] < other.digits[0]

    def __le__(self, other):
        for digit in len(self.digits):
            if self.digits[digit] > other.digits[digit]:
                return False
        return True

    def unique(self):
        for digit in self.digits:
            if digit.range != Digit.Range.Number:
                return False
        return True

    def increase(self, position):
        self.digits[position].increase()


if __name__ == "__main__":
    aye = 0
    nay = 0

    v123 = Version('1.2.3')
    v124 = Version('1.2.4')

    aye += v123 < v124
    nay += v123 == v124
    nay += v123 > v124

    nay += v124 < v123
    nay += v124 == v123
    aye += v124 > v123

    if nay or aye != 2:
        print('fail (%i)' % aye)
    else:
        print('pass')

    aye = 0

    aye += Version('1.2.>=3') == Version('1.2.3')
    aye += Version('1.2.>=3') == Version('1.2.<=3')
    nay += Version('1.2.>3') == Version('1.2.<=3')
    aye += Version('*.2.>3') == Version('1.2.<3')
    aye += Version('1.2.3') == Version('1.*.4')
    aye += Version('1.>2.3') == Version('1.3.3')
    aye += Version('1.3.3') == Version('1.>2.3')
    nay += Version('1.2.3') == Version('1.>2.3')

    if nay or aye != 6:
        print('fail simple range equality test (%i/%i)' % (nay, aye))
    else:
        print('pass')

    aye = 0

    aye += Version('1.>2.3') == Version('1.3.3')

    if nay or aye != 1:
        print('fail simple range equality test (%i/%i)' % (nay, aye))
    else:
        print('pass')

    aye = 0

    aye += Version('*') == Version('1.2.3')
    aye += Version('1.*') == Version('1.2.3')
    aye += Version('1.2.*') == Version('1.2.3')

    aye += Version('1.2.3') == Version('*')
    aye += Version('1.2.3') == Version('1.*')
    aye += Version('1.2.3') == Version('1.2.*')

    if nay or aye != 6:
        print('fail wildchar test (%i/%i)' % (nay, aye))
    else:
        print('pass')
