"""
Timecard is a framework for rendering tables wih metric values or any other
data to console.

The output looks like that of dstat (http://dag.wiee.rs/home-made/dstat/).
It is also possible to save data to cvs file.

Example:
    python -m timecard.sample
"""
__author__ = "Konstantin Enchant <sirkonst@gmail.com>"
# ------------------------------------------------------------------------------
from sys import stdout
from time import time
from datetime import datetime
import csv
from collections import OrderedDict
from contextlib import contextmanager
# ------------------------------------------------------------------------------
__about__ = __doc__
__all__ = (
    "Int", "Float", "AutoDateTime", "AutoDeltaTime", "MultiMetric",
    "TotalAndSec", "Timecard", "Bytes", "Traffic", "Timeit", "__about__"
)
# ------------------------------------------------------------------------------

_ansi = {
    "reset": "\033[0;0m",
    "underline": "\033[4m",
    "reverse": "\033[2m",
    "high": "\033[1m",

    "darkblue": "\033[0;34m",
    "darkcyan": "\033[0;36m",
    "blue": "\033[1;34m",
    "green": "\033[0;32m",
    "green_high": "\033[1;32m",
    "gray": "\033[0;37m",
}


class _MetricBase(object):
    """
    Base class for all metrics.

    :param str title: title for metric
    :param str subtitle: additional title (or empty)
    """
    value = None
    value_type = None
    width = 0

    def __init__(self, title, subtitle=""):
        self.title = title
        self.subtitle = subtitle
        self._rendered_title = None
        self._rendered_subtitle = None

    def render_title(self):
        if self._rendered_title:
            return self._rendered_title

        if not self._rendered_subtitle:
            self.render_subtitle()

        self._rendered_title = _ansi["blue"]\
            + self.title.center(self.width, "-") + _ansi["reset"]
        return self.render_title()

    def render_subtitle(self):
        if self._rendered_subtitle:
            return self._rendered_subtitle

        self.width = max(
            self.width,
            self.subtitle and len(self.subtitle) or 0
        )
        if self.width < len(self.title):
            self.width = len(self.title) + 2

        self._rendered_subtitle = _ansi["darkcyan"] + _ansi["underline"] \
            + self.subtitle.rjust(self.width) + _ansi["reset"]
        return self._rendered_subtitle

    def _render_cell(self):
        """
        Aligns value in table cell.
        """
        return str(self).rjust(self.width)

    def render_value(self, fix):
        """
        Renders value for console output.

        :param bool fix: is a committed value?
        """
        color = fix and _ansi["green_high"] or _ansi["green"]
        s = color + self._render_cell() + _ansi["reset"]
        return s

    def to_csv(self):
        """
        Converts value for saving to cvs file.
        """
        return str(self)

    def reset(self):
        """
        This functions is called after writing a committed value. 
        It can be overdriven in subclass.
        """
        pass

    def __str__(self):
        """
        Converts value for console output.
        """
        if self.value is None:
            return " "
        else:
            return str(self.value)

    def __iadd__(self, value):
        """
        Implements += operation for metric.
        """
        if self.value is None:
            self.value = value
        else:
            self.value += value

    def __isub__(self, value):
        """
        Implements -= operation for metric.
        """
        if self.value is None:
            self.value = value
        else:
            self.value -= value

    def _compare(self, other, method):
        """
        Helps to compare metrics.
        """
        return method(self.value, other)

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)


class Int(_MetricBase):
    """
    Integer metric.
    """
    width = 7
    value = 0
    value_type = int


class Bytes(Int):
    """
    Metric for size or traffic, rendered with prefixes.
    """

    def __str__(self):
        n = self.value
        if n:
            frmt = "%(value).2f%(symbol)s"
            symbols = ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
            prefix = {}
            for i, s in enumerate(symbols[1:]):
                prefix[s] = 1 << (i+1)*10
            for symbol in reversed(symbols[1:]):
                if n >= prefix[symbol]:
                    value = float(n) / prefix[symbol]
                    return frmt % locals()
            return frmt % dict(symbol=symbols[0], value=n)
        else:
            return " "

    def to_csv(self):
        return str(self.value)


class Float(_MetricBase):
    """
    Floating-point metric.
    """
    width = 6
    value = 0.0
    value_type = float

    def __str__(self):
        if self.value is None:
            return " "
        return "{:.1f}".format(self.value)


class DeltaTime(Float):
    """
    Metric for time values, rendered with prefixes.
    """
    value = None
    width = 6

    def __str__(self):
        if self.value is None:
            return " "

        if self.value < 0.1:
            return "{:.0f}ms".format(self.value * 1000)
        elif self.value < 60:
            return "{:.2f}s".format(self.value)
        else:
            return "{:.1f}m".format(self.value / 60)

    def to_csv(self):
        if self.value is None:
            return ""
        return str(self.value)


class AutoDateTime(_MetricBase):
    """
    Current time and date.

    You can suppress output of date to console by setting flag show_date=True.
    In csv file date will always be written even if flag is set.

    :param bool show_date: show date in console output?
    """
    frm_full = "%Y-%m-%d %H:%M:%S"
    frm_time = "%H:%M:%S"

    def __init__(self, title="time", show_date=True):
        super(AutoDateTime, self).__init__(title)
        self._show_data = show_date
        self.width = show_date and 19 or 8

    @property
    def value(self):
        return datetime.now()

    def __str__(self):
        if self._show_data:
            return self.value.strftime(self.frm_full)
        else:
            return self.value.strftime(self.frm_time)

    def to_csv(self):
        return self.value.strftime(self.frm_full)


class AutoDeltaTime(DeltaTime):
    """
    Metric to calculate time between two calls (render).
    """

    def __init__(self, title="delta"):
        super(AutoDeltaTime, self).__init__(title)
        self._last = time()

    def render_value(self, fix):
        now = time()
        self.value = now - self._last
        self._last = now
        return super(AutoDeltaTime, self).render_value(fix)


class _OrderedMetrics(OrderedDict):

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        orig = lambda: \
            super(_OrderedMetrics, self).__setitem__(
                key, value, dict_setitem=dict_setitem)

        if value is isinstance(value, _MetricBase):
            return orig()

        try:
            item = self[key]
        except LookupError:
            return orig()
        else:
            if isinstance(item, _MetricBase):
                if value is not None:
                    assert item.value_type, "Not support set value"
                    item.value = item.value_type(value)
                else:
                    return item
            else:
                return orig()

    def __setattr__(self, name, value):
        if (
            name in self
            or isinstance(value, _MetricBase)
        ):
            return self.__setitem__(name, value)
        else:
            return super(_OrderedMetrics, self).__setattr__(name, value)

    def __getattribute__(self, name):
        if name in self:
            return self[name]
        else:
            return super(_OrderedMetrics, self).__getattribute__(name)


class MultiMetric(_MetricBase, _OrderedMetrics):
    """
    Encapsulates selected metrics under one title.
    """

    def __init__(self, title):
        _OrderedMetrics.__init__(self)
        _MetricBase.__init__(self, title)

    def render_subtitle(self):
        if self._rendered_subtitle:
            return self._rendered_subtitle

        if len(self) == 1:
            if self.values()[0].width < len(self.values()[0].title):
                self.values()[0].width = len(self.values()[0].title)

        buff = []
        width = 0
        for m in self.values():
            subtitle = m.title
            w = m.width
            if w < len(subtitle):
                w = len(subtitle)
            s = subtitle.rjust(w)
            buff.append(
                _ansi["darkcyan"]
                + _ansi["underline"] + s + _ansi["reset"]
            )
            m.width = w
            width += m.width

        self.width = width + len(self) - 1

        self._rendered_subtitle = " ".join(buff)
        return self._rendered_subtitle

    def render_value(self, fix):
        color = fix and _ansi["green_high"] or _ansi["green"]
        buff = []
        for m in self.values():
            buff.append(
                color + m._render_cell() + _ansi["reset"]
            )
        return " ".join(buff)


class TotalAndSec(MultiMetric):
    """
    Metric for measuring the absolute value and calculating its temporal
    variation.
    """
    type_total = Int
    type_persec = Float

    def __init__(self, title):
        super(TotalAndSec, self).__init__(title)
        self._last_snap = 0
        self._last_time = time()

        self.total = self.type_total("total")
        self.persec = self.type_persec("/sec")
        self.reset()

    def reset(self):
        self.persec.value = None

    @property
    def value(self):
        return self.total

    @value.setter
    def value(self, value):
        self.total = value

    def __iadd__(self, value):
        self.total += value

    def __isub__(self, value):
        self.total += value

    def calc(self):
        now = time()
        if not self._last_time:
            self._last_snap = self.total.value
            self._last_time = now
            return

        td = now - self._last_time
        if td < 0.9:
            return

        delta = (self.total.value - self._last_snap) / td
        self._last_snap = self.total.value
        self._last_time = now
        self.persec = delta

    def render_value(self, fix):
        if fix:
            self.calc()
        return super(TotalAndSec, self).render_value(fix)


class Traffic(TotalAndSec):
    """
    Metrics for traffic size and traffic speed.
    """
    type_total = Bytes
    type_persec = Bytes


class Timeit(MultiMetric):
    """
    Metric for calculating time of execution of any function. It is used as
    context manager.

    Output includes min, average and max values. If list of limits is set,
    it is  also included. Values are reset after they are fixed.

    :param list limits: list of limit
    """

    def __init__(self, title, limits=None):
        super(Timeit, self).__init__(title)
        self._reset = True
        self.min = DeltaTime("min")
        self.average = DeltaTime("avr")
        self.max = DeltaTime("max")
        if limits:
            self._limits = list(reversed(sorted(limits)))
            for lim in reversed(self._limits):
                self[str(lim)] = Int(">{:.1f}s".format(lim))
        else:
            self._limits = []
        self.reset()

    def reset(self):
        self.min.value = None
        self.max.value = None
        self.average.value = None
        for lim in self._limits:
            self[str(lim)].value = 0

    @contextmanager
    def __call__(self, exception_ok=False):
        s = time()
        exc = None
        try:
            yield
        except Exception as e:
            exc = e
        finally:
            if exc and exception_ok is not True:
                raise exc

            delta = time() - s

            if self.max.value is None:
                self.min = delta
                self.average = delta
                self.max = delta
            else:
                if delta < self.min:
                    self.min = delta
                elif delta > self.max:
                    self.max = delta
                self.average = (self.average.value + delta) / 2

            for lim in self._limits:
                if delta >= lim:
                    self[str(lim)] += 1
                    break

            if exc:
                raise exc

    def render_value(self, fix):
        return super(Timeit, self).render_value(fix)


class Timecard(_OrderedMetrics):
    """
    Class for collecting, rendering and managing metrics.

    :param str csvfile: path for writing csv file (option)
    """

    def __init__(self, csvfile=None):
        super(Timecard, self).__init__()
        self._csvfile = csvfile
        self._last_line_fixed = False

    def _write_csv_row(self, values, rewrite=False):
        mode = rewrite and "wb" or "ab"
        with open(self._csvfile, mode) as f:
            csv.writer(f).writerow(values)

    def write_headers(self):
        """
        Output table header to console and csv file (if present).
        """
        h1 = []
        h2 = []
        for m in self.values():
            h2.append(m.render_subtitle())
            h1.append(m.render_title())

        stdout.write(" ".join(h1))
        stdout.write("\n\r")
        c = _ansi["gray"] + "|" + _ansi["reset"]
        stdout.write(c.join(h2))
        stdout.write("\n\r")
        stdout.flush()

        if self._csvfile:
            header_row = []
            for m in self.values():
                if isinstance(m, MultiMetric):
                    for subm in m.values():
                        header_row.append(
                            "{}_{}".format(m.title, subm.title)
                        )
                else:
                    if m.subtitle:
                        header_row.append(
                            "{}_{}".format(m.title, m.subtitle)
                        )
                    else:
                        header_row.append(m.title)
            self._write_csv_row(header_row, rewrite=True)

    def write_line(self, fix=True):
        """
        Output line containing values to console and csv file.

        Only committed values are written to css file.

        :param bool fix: to commit measurement values
        """
        cells = []
        csv_values = []
        for m in self.values():
            cells.append(m.render_value(fix=fix))
            if isinstance(m, MultiMetric):
                for sub in m.values():
                    csv_values.append(sub.to_csv())
            else:
                csv_values.append(m.to_csv())
            if fix:
                m.reset()

        if fix and self._csvfile:
            self._write_csv_row(csv_values)

        c = _ansi["gray"] + "|" + _ansi["reset"]

        if self._last_line_fixed:
            stdout.write("\n\r")
        else:
            stdout.write("\r")

        if not fix:
            stdout.write(_ansi["reverse"])

        stdout.write(c.join(cells))
        stdout.flush()

        self._last_line_fixed = fix
