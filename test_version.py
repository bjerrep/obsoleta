from version import Version
from common import Position

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
    print('failed plain numbers (%i/%i)' % (nay, aye))
    exit(1)

# ------------------------------------------

aye = 0

aye += Version('1.2.>=3') == v123
aye += Version('1.2.>=3') == Version('1.2.<=3')
nay += Version('1.2.>3') == Version('1.2.<=3')
aye += Version('1.2.>=3') == Version('1.2.>=3')

aye += Version('1.>2.3') == Version('1.3.3')
aye += Version('1.3.3') == Version('1.>2.3')
nay += v123 == Version('1.>2.3')

if nay or aye != 5:
    print('failed simple range equality test (%i/%i)' % (nay, aye))
    exit(1)

# ------------------------------------------

aye = 0

aye += Version('*') == Version('*')
aye += Version('1.*') == Version('1.*')
aye += Version('1.3.3') == Version('1.*')
aye += Version('1.1.*') == Version('1.1.*')
aye += Version('*.2.>3') == Version('1.2.<3')
aye += Version('1.*.4') == v123
aye += Version('1.2.3') == Version('1.*.4')
aye += v123 > Version('1.*')
aye += v123 >= Version('1.*')

aye += Version('*') == v123
aye += Version('1.*') == v123
aye += Version('1.2.*') == v123

aye += v123 == Version('*')
aye += v123 == Version('1.*')
aye += v123 == Version('1.2.*')

aye += Version('*') > v123
aye += Version('*') < v123
aye += v123 > Version('*')
aye += v123 < Version('*')

if nay or aye != 19:
    print('fail wildchar test (%i/%i)' % (nay, aye))
    exit(1)

# ------------------------------------------

try:
    _ = str(Version('1.2').increase(Position.MINOR))
except:
    print('fail version other tests')
    exit(1)
