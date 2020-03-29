#!/usr/bin/env python3
from enum import Enum
from common import Position
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

        if not digit_string[0].isdigit():
            if digit_string == '*':
                self.range = Digit.Range.Any
            else:
                self.range = Digit.Range.Range
                if not digit_string[1].isdigit():
                    self.op = digit_string[:2]
                    self.number = int(digit_string[2:])
                else:
                    self.op = digit_string[0]
                    self.number = int(digit_string[1:])
        else:
            self.range = Digit.Range.Number
            self.op = "=="
            self.number = int(digit_string)

    def __str__(self):
        if self.range == Digit.Range.Any:
            return '*'
        elif self.range == Digit.Range.Number:
            return str(self.number)
        return self.op + str(self.number)

    def __eq__(self, other):
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

        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return Match.Larger

    def __lt__(self, other):
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

        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return Match.Smaller

    def increase(self):
        self.number += 1

    def reset(self):
        self.number = 0


class Version:
    def __init__(self, version=None):
        if isinstance(version, Version):
            self.digits = copy.deepcopy(version.digits)
            return
        self.string = version
        self.digits = [Digit(digit) for digit in version.split('.')]

    def __str__(self):
        if self.string:
            return self.string
        self.string = ".".join(map(str, self.digits))
        return self.string

    def __eq__(self, other):
        for a, b in zip(self.digits, other.digits):
            match = a == b
            if match == Match.Larger:
                return True
            if match == Match.Smaller:
                return False
        return True

    def __lt__(self, other):
        # less than
        for a, b in zip(self.digits, other.digits):
            try:
                match = a < b
            except:
                return True
            if match == Match.Smaller:
                return True
            if match == Match.Larger:
                return False

        return False

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def unique(self):
        for digit in self.digits:
            if digit.range != Digit.Range.Number:
                return False
        return True

    def increase(self, position):
        self.string = None
        self.digits[position.value].increase()
        if common.get_setup() and common.get_setup().semver:
            if position == Position.MINOR:
                self.digits[Position.BUILD.value].reset()
            elif position == Position.MAJOR:
                self.digits[Position.MINOR.value].reset()
                self.digits[Position.BUILD.value].reset()
        return self

    def set(self, position, value):
        self.string = None
        self.digits[position.value] = Digit(value)
