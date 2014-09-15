from time import sleep
from random import randint

from timecard import *


def sample():
    table = Timecard("test.csv")
    table.time = AutoDateTime(show_date=False)
    table.delta = AutoDeltaTime()
    table.timeit = Timeit("timeit", [0.2, 0.5, 1])
    table.count = Int("count")
    table["float"] = Float("float")
    table.foo = TotalAndSec("foo")
    table.foo.bar = Int("bar")
    table.rand = MultiMetric("random")
    table.rand["a"] = Int("a")
    table["rand"].b = Int("b")
    table["rand"]["c"] = Int("c")
    table.bytes = Bytes("bytes")
    table.traffic = Traffic("traffic")

    table.write_headers()
    i = 0
    while True:
        table["count"] += 1
        table.float += 0.1
        table.foo += randint(0, 100)
        table.foo.bar += randint(0, 100)
        table["rand"]["a"] = randint(0, 100)
        table.rand["b"] = randint(0, 100)
        table["rand"].c = randint(0, 100)
        table.bytes = randint(0, 1000000)
        table.traffic += randint(0, 1000000)

        def _func():
            sleep(0.01)

        with table.timeit():
            for _ in xrange(randint(0, 100)):
                _func()

        sleep(1)
        i += 1
        if i == 5:
            i = 0
            table.write_line(fix=True)
        else:
            table.write_line(fix=False)


if __name__ == "__main__":
    try:
        sample()
    except KeyboardInterrupt:
        print "\n"