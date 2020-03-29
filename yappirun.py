import yappi
from log import war


def start_yappi():
    war("starting yappi")
    yappi.set_clock_type('wall')
    yappi.start()


def stop_yappi():
    yappi.stop()
    war('writing /tmp/yappi.callgrind')
    stats = yappi.get_func_stats()
    stats.save('/tmp/yappi.callgrind', 'callgrind')
