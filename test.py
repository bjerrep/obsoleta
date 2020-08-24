#!/usr/bin/env python3
# flake8: noqa F401

if __name__ == '__main__':
    import time

    start_time = time.time()

    import test_package
    import test_version
    import test_obsoleta
    import test_dixi
    import test_obsoleta_api
    import test_dixi_api
    import version
    #import test_c_generator

    print('\n\nsuccess, all tests took %.3f secs\n' % (time.time() - start_time))
