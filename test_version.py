from version import Version


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
    exit(1)

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
    exit(1)

aye = 0

aye += Version('1.>2.3') == Version('1.3.3')

if nay or aye != 1:
    print('fail simple range equality test (%i/%i)' % (nay, aye))
    exit(1)

aye = 0

aye += Version('*') == Version('1.2.3')
aye += Version('1.*') == Version('1.2.3')
aye += Version('1.2.*') == Version('1.2.3')

aye += Version('1.2.3') == Version('*')
aye += Version('1.2.3') == Version('1.*')
aye += Version('1.2.3') == Version('1.2.*')

aye += Version('*') > Version('1.2.3')
aye += Version('*') < Version('1.2.3')
aye += Version('1.2.3') > Version('*')
aye += Version('1.2.3') < Version('*')


if nay or aye != 10:
    print('fail wildchar test (%i/%i)' % (nay, aye))
    exit(1)
