#!/usr/bin/env python3
from enum import Enum
from errorcodes import ErrorCode
from common import Exceptio, Position
import common
import copy


class Match(Enum):
    Larger = 0
    Equal = 1
    Smaller = 2


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
            return Match.Larger

        if self.range == Digit.Range.Number and other.range == Digit.Range.Number:
            if self.number == other.number:
                return Match.Equal
            return Match.Smaller

        if self.range == Digit.Range.Range:
            res = eval("%i%s%i" % (other.number, self.op, self.number))
            if not res:
                return Match.Smaller
            return Match.Larger

        if other.range == Digit.Range.Range:
            res = eval("%i%s%i" % (self.number, other.op, other.number))
            if not res:
                return Match.Smaller
            return Match.Larger

    def __lt__(self, other):
        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return Match.Smaller

        if self.range == Digit.Range.Number and other.range == Digit.Range.Number:
            if self.number < other.number:
                return Match.Smaller
            if self.number > other.number:
                return Match.Larger
            return Match.Equal

        if self.range == Digit.Range.Range:
            res = eval("%i%s%i" % (other.number, self.op, self.number))
            if not res:
                return Match.Larger
            return Match.Smaller

        if other.range == Digit.Range.Range:
            res = eval("%i%s%i" % (self.number, other.op, other.number))
            if not res:
                return Match.Larger
            return Match.Smaller

    def increase(self):
        self.number += 1

    def reset(self):
        self.number = 0


class Version:
    def __init__(self, version='*.*.*'):
        if isinstance(version, Version):
            self.digits = copy.deepcopy(version.digits)
            return
        self.digits = []
        digits = version.split('.')
        if digits != [d for d in digits if d]:
            raise Exceptio(
                'Invalid version number %s (try compact name with "" if running from a shell and using e.g. ">")'
                % version, ErrorCode.INVALID_VERSION_NUMBER)
        nof_digits = len(digits)
        if not nof_digits:
            self.digits.append(Digit(version))
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
            match = self.digits[digit] == other.digits[digit]
            if match == Match.Larger:
                return True
            if match == Match.Smaller:
                return False
        return True

    def __lt__(self, other):
        # less than
        for digit in range(len(self.digits)):
            try:
                match = self.digits[digit] < other.digits[digit]
            except:
                return True
            if match == Match.Smaller:
                return True
            if match == Match.Larger:
                return False

        return self.digits[0] < other.digits[0]

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def unique(self):
        for digit in self.digits:
            if digit.range != Digit.Range.Number:
                return False
        return True

    def increase(self, position):
        self.digits[position.value].increase()
        if common.get_setup().semver:
            if position == Position.MINOR:
                self.digits[Position.BUILD.value].reset()
            elif position == Position.MAJOR:
                self.digits[Position.MINOR.value].reset()
                self.digits[Position.BUILD.value].reset()
        return self

    def set(self, position, value):
        self.digits[position.value] = Digit(value)
