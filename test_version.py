from common import Position
from version import Version, VersionAny


# ------------------------------------------
# Figure out who has the most significant version requirement
aye = 0
nay = 0

nay += Version('2.0.>=0').more_significant_than(Version('2.0.>0'))   # False
aye += Version('2.0.>0').more_significant_than(Version('2.0.>=0'))   # True

aye += Version('2.0.>=1').more_significant_than(Version('2.0.>=0'))  # True
nay += Version('2.0.>=0').more_significant_than(Version('2.0.>=1'))  # False

nay += Version('2.0.>=0').more_significant_than(Version('2.0.1'))    # False
aye += Version('2.0.1').more_significant_than(Version('2.0.>=0'))    # True

if nay or aye != 3:
    print(f'Figure out who has the most significant version requirement ({nay}/{aye})')
    exit(1)



# ------------------------------------------
# Comparing versions that do not overlap
aye = 0
nay = 0

nay += Version('2.0.1') >= Version('>=2.>=0.>=2')   # False
nay += Version('1.2.<3') > Version('1.2.>=3')       # False
nay += Version('1.2.<3') == Version('1.2.>=3')      # False
nay += Version('1.2.>3') == Version('1.2.<=3')      # False
aye += Version('1.2.<3') < Version('1.2.>=3')       # True. Or what

if nay or aye != 1:
    print(f'Comparing versions that have no overlap ({nay}/{aye})')
    exit(1)



# ------------------------------------------
# Straight no fuzz version comparisons

aye = 0
nay = 0

v123 = Version('1.2.3')
v124 = Version('1.2.4')

aye += v123 == v123
aye += v123 < v124
nay += v123 == v124
nay += v123 > v124

nay += v124 < v123
nay += v124 == v123
aye += v124 > v123

aye += v124 >= v123
aye += v123 >= v123
aye += v123 <= v124
aye += v123 <= v123

nay += v124 <= v123
nay += v123 >= v124

if nay or aye != 7:
    print(f'failed plain numbers ({nay}/{aye})')
    exit(1)


# ------------------------------------------
# Straight no fuzz version comparisons - ranged
aye = 0
nay = 0

aye += Version('1.2.>=3') == v123
aye += Version('1.2.>=3') == Version('1.2.<=3')
aye += Version('1.2.>=3') == Version('1.2.>=3')

aye += Version('1.>2.3') == Version('1.3.3')
aye += Version('1.3.3') == Version('1.>2.3')

aye += Version('1.2.3') >= Version('>=1.>=2.>=3')
aye += Version('2.2.3') >= Version('>=1.>=2.>=3')
aye += Version('1.3.3') >= Version('>=1.>=2.>=3')
aye += Version('1.2.4') >= Version('>=1.>=2.>=3')

aye += Version('1.2.3') == Version('>=1.>=2.>=3')
aye += Version('2.2.3') == Version('>=1.>=2.>=3')
aye += Version('1.3.3') == Version('>=1.>=2.>=3')
aye += Version('1.2.4') == Version('>=1.>=2.>=3')

aye += Version('2.0.0') > Version('>=1.>=2.>=3')
nay += Version('2.0.0') < Version('>=1.>=2.>=3')
aye += Version('1.3.0') > Version('>=1.>=2.>=3')
aye += Version('1.2.4') > Version('>=1.>=2.>=3')

aye += Version('>=1.>=2.>=3') == Version('2.0.0')
aye += Version('>=1.>=2.>=3') == Version('1.3.0')
aye += Version('>=1.>=2.>=3') == Version('1.2.4')

aye += Version('2.0.1') < Version('>=2.>=0.>=2')
nay += Version('3.0.1') < Version('>=2.>=0.>=2')
nay += Version('>=2.>=0.>=2') <= Version('2.0.1')
aye += Version('>=2.>=0.>=2') > Version('2.0.1')

nay += v123 == Version('1.>2.3')

if nay != 0 or aye != 21:
    print(f'failed simple range equality test ({nay}/{aye})')
    exit(1)

# ------------------------------------------
# wildchars
aye = 0
nay = 0

aye += VersionAny == VersionAny
aye += Version('1.*') == Version('1.*')
aye += Version('1.3.3') == Version('1.*')
aye += Version('1.1.*') == Version('1.1.*')
aye += Version('*.2.>3') == Version('1.2.<3')
aye += Version('1.*.4') == v123
aye += Version('1.2.3') == Version('1.*.4')
aye += v123 > Version('1.*')
aye += v123 >= Version('1.*')

aye += VersionAny == v123
aye += Version('1.*') == v123
aye += Version('1.2.*') == v123

aye += v123 == VersionAny
aye += v123 == Version('1.*')
aye += v123 == Version('1.2.*')

aye += VersionAny > v123
aye += VersionAny < v123
aye += v123 > VersionAny
aye += v123 < VersionAny

if nay or aye != 19:
    print(f'fail wildchar test ({nay}/{aye})')
    exit(1)

# ------------------------------------------
# api get_change()
aye = 0

aye += not Version('1.2.3').get_change('1.2.3')
aye += Version('1.2.3').get_change('1.2.4') == Position.BUILD
aye += Version('1.2.3').get_change('1.3.3') == Position.MINOR
aye += Version('1.2.3').get_change('2.2.3') == Position.MAJOR
aye += Version('>=1.2.3').get_change('>=2.2.3') == Position.MAJOR

if aye != 5:
    print('api: get_change failed')
    exit(1)

# ------------------------------------------
# api increase()
aye = 0

aye += Version('1.2').increase(Position.MINOR) == Version('1.3')

if aye != 1:
    print('api: increase()')
    exit(1)

print('test version: pass')
