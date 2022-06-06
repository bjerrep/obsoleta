#!/usr/bin/env python3
# flake8: noqa F401

if __name__ == '__main__':
    import time

    start_time = time.time()
    import obsoleta.test.test_package
    import obsoleta.test.test_version
    import obsoleta.test.test_obsoleta_py
    import obsoleta.test.test_dixi
    import obsoleta.test.test_obsoleta_api
    import obsoleta.test.test_obsoleta_api_print
    import obsoleta.test.test_obsoleta_api_listmissing
    import obsoleta.test.test_dixi_api
    # import obsoleta.test.test_c_generator

    print('\n\nsuccess, all tests took %.3f secs\n' % (time.time() - start_time))
