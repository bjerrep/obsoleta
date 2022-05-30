#!/usr/bin/env python3
import copy
from enum import Enum
from common import Position
import common
import exceptions


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
                self.op = "=="
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
        if self.range == Digit.Range.Number:
            return str(self.number)
        return self.op + str(self.number)

    def __eq__(self, other):
        if self.range == Digit.Range.Number and other.range == Digit.Range.Number:
            if self.number == other.number:
                return Match.Equal
            return Match.Smaller

        if self.range == Digit.Range.Range:
            res = eval(f'{other.number}{self.op}{self.number}')
            if not res:
                return Match.Smaller
            return Match.Larger

        if other.range == Digit.Range.Range:
            res = eval(f'{self.number}{other.op}{other.number}')
            if not res:
                return Match.Smaller
            return Match.Larger

        if self.range == Digit.Range.Any or other.range == Digit.Range.Any:
            return Match.Larger
        return Match.Smaller

    def corrected_number(self):
        """
        Called corrected in lack of a better word. Use that e.g. x > N is x >= N+1
        """
        if self.op == '>':
            return self.number + 1
        if self.op == '<':
            if self.number == 0:
                raise exceptions.InvalidVersionNumber('found a "<0" which makes no sense')
            return self.number - 1
        return self.number

    def __lt__(self, other):
        self_number = self.number
        if self.op == '>':
            self_number += 1
        elif self.op == '<':
            self_number -= 1

        other_number = other.number
        if other.op == '>':
            other_number += 1
        elif other.op == '<':
            other_number -= 1

        if self_number < other_number:
            return Match.Smaller
        if self_number > other_number:
            return Match.Larger
        return Match.Equal

    def value(self):
        return self.number

    def increase(self):
        self.number += 1

    def reset(self):
        self.number = 0

    def op_more_significant_than(self, other):
        if self.op == other.op:
            return self.number >= other.number
        if self.number > other.number:
            return True
        if self.number < other.number:
            return False
        if (self.op == '==') or (self.op == '>'):
            return True
        return False

    def truly_equal(self, other):
        if self.number == other.number and self.op == other.op:
            return True
        return False


class Version:
    as_string = None

    def __init__(self, version=None):
        if isinstance(version, Version):
            self.digits = copy.deepcopy(version.digits)
            return
        self.as_string = version
        self.digits = [Digit(digit) for digit in version.split('.')]

    def __repr__(self):
        if self.as_string:
            return self.as_string
        self.as_string = ".".join(map(str, self.digits))
        return self.as_string

    def __eq__(self, other):
        for a, b in zip(self.digits, other.digits):
            if a.corrected_number() == b.corrected_number():
                continue
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

    def is_any(self):
        return self.as_string == '*'

    def increase(self, position):
        self.digits[position.value].increase()
        if common.get_conf() and common.get_conf().semver:
            if position == Position.MINOR:
                self.digits[Position.BUILD.value].reset()
            elif position == Position.MAJOR:
                self.digits[Position.MINOR.value].reset()
                self.digits[Position.BUILD.value].reset()
        # Not a joke. Python 3.9.7 really dislikes the as_string member variable.
        # Try to set it to None and observe that it really doesn't like to get modified. Why ?!?!?
        self.as_string = ".".join(map(str, self.digits))
        return self

    def set(self, position, value):
        self.as_string = None
        self.digits[position.value] = Digit(value)

    def get_change(self, other):
        """
        Returns Position of most important difference or None if the versions match.
        Note: Raises an exception if it is not given 3 digit versions to work with.
        """
        if isinstance(other, str):
            other = Version(other)
        if self.digits[Position.MAJOR.value].value() != other.digits[Position.MAJOR.value].value():
            return Position.MAJOR
        if self.digits[Position.MINOR.value].value() != other.digits[Position.MINOR.value].value():
            return Position.MINOR
        if self.digits[Position.BUILD.value].value() != other.digits[Position.BUILD.value].value():
            return Position.BUILD
        return None

    def more_significant_than(self, other):
        for digita, digitb in zip(self.digits, other.digits):
            if not digita.truly_equal(digitb):
                if digita.value() == digitb.value():
                    return digita.op_more_significant_than(digitb)
                return digita.value() > digitb.value()

        return True


VersionAny = Version('*')
