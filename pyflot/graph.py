# -*- coding: utf-8 -*-
"""
    pyflot.graph

    This module implements the main classes.

    :copyright: (c) 2011 by Brian Luft
    :license: MIT, see LICENSE for more details.
"""

import collections
from datetime import date
from functools import partial
from itertools import chain
import inspect
import json
import time


__title__ = 'pyflot'
__version__ = '0.2.2'
__author__ = 'Brian Luft'
__license__ = 'MIT'
__copyright__ = 'Copyright 2011 Brian Luft'


def update(d, u):
    """
    Recursively update nested dicts

    Credit: Alex Martelli
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class MissingDataException(Exception):
    """Exception raised when a series does not contain
    any data points"""


class DuplicateLabelException(Exception):
    """Exception raised when an attempt is made to 
    label a new series with a label already in use"""


LINE_TYPES = ('bars', 'lines', 'points')


class Flot(object):
    """
    Represents a ``flot`` graph

    This is a Python representation of a flot graph with the
    goal preserving the flot attribute names and organization
    of the options. A Flot instance will allow you to 
    use your Python data structures as is and will handle
    the details of converting to valid JSON with items 
    formatted properly for ``flot``. (Handy for time series
    for example)
    """

    def __init__(self):
        self._series = []
        self._options = {}

        #apply any options specified starting with the top
        #of the inheritance chain
        bases = list(inspect.getmro(self.__class__))
        bases.reverse()
        for base in bases:
            if hasattr(base, 'options'):
                update(self._options, base.options)

    @property
    def series_json(self):
        """
        Returns a string with each data series
        associated with this graph formatted as JSON, 
        suitable for passing to the ``$.plot`` method.
        """
        return json.dumps(self.series)

    @property
    def series(self):
        """
        Returns a string with each data series
        associated with this graph, 
        suitable for passing to the ``json.dumps`` method.
        """
        return [self.prepare_series(s) for s in self._series]

    @property
    def options_json(self):
        """
        Returns a JSON string representing the global options
        for this graph in a format suitable for passing to 
        the ``$.plot`` method as the options parameter.
        """
        return json.dumps(self._options)

    def __getattr__(self, value):
        """
        add_bars
        add_line
        add_points

        provides shortcut methods for adding series using a particular line type
        """
        if value.startswith('add_'):
            if value.split('_')[1] in LINE_TYPES:
                return partial(self.add_series_type, value[4:])
        raise AttributeError

    def add_series_type(self, line_type, series, label=None, **kwargs):
        """Used as a partial by __getattr__ to auto set the line_type
        for the series."""
        method = getattr(self, 'add_series')
        return method(series, label, **{line_type: True})

    def add_series(self, series, label=None, options=None, **kwargs):
        """
        A series is a list of pairs (2-tuples)

        Optional Args:
            bars
            line
            points - for each of these present as keyword arguments,
                     their value should be a dict representing the 
                     line type options relative to their type. 
                     Alternatively, if the value is `True` the option 
                     for showing the line type {'show': True} will
                     be set for the options for this line type.
            options: Add option to the graph (like color)
        """
        if type(series) is not int and not series:
            raise MissingDataException

        # Check if itsn't a single value (for pie charts)
        if type(series) is list:
            #detect time series
            testatom = series[0][0]
            if isinstance(testatom, date):
                series = [(int(time.mktime(ts.timetuple()) * 1000), val) \
                            for ts, val in series]
                self._options['xaxis'] = {'mode': 'time'}

        new_series = {'data': series}
        if label and label in [x.get('label', None) for x in self._series]:
            raise DuplicateLabelException
        elif label:
            new_series.update(label=label)
        for line_type in LINE_TYPES:
            if line_type in kwargs:
                if isinstance(kwargs[line_type], collections.Mapping):
                    new_series.update({line_type: kwargs[line_type]})
                else:
                    new_series.update({line_type: {'show': True}})
        if options is not None:
            if type(options) is dict:
                new_series.update(options)
        self._series.append(new_series)

    #def add_time_series(self, series, label=None, **kwargs):
        #"""
        #A specialized form of ``add_series`` for adding time-series data.

        #Flot requires times to be specified in Javascript timestamp format.
        #This convenience function lets you pass datetime instances and handles
        #the conversion. It also sets the correct option to indicate to ``flot``
        #that the graph should be treated as a time series
        #"""
        #_series = [(int(time.mktime(ts.timetuple()) * 1000), val) \
                    #for ts, val in series]
        #self._options['xaxis'] = {'mode': 'time'}
        #return self.add_series(_series, label, **kwargs)

    def calculate_bar_width(self):
        """Determines which series has the most data points and then
        calculates a width for bars based on the range for `x` for that
        series. Flot treats the barWidth setting in terms of graph
        units (not pixels)."""
        slices = max([len(s['data']) for s in self._series])
        xs = [pair[0] for pair in chain(*[s['data'] for s in self._series])]
        xmin, xmax = (min(xs), max(xs))
        w = xmax - xmin
        return float(w)/slices

    def prepare_series(self, series):
        """Called for each series when the data is being serialized to 
        JSON. Override to set any options based on characteristics of the
        series.

        Currently used to ensure that any bars series get a consistent
        barWidth."""
        if 'bars' in series:
            w = self.calculate_bar_width()
            if w:
                series['bars']['barWidth'] = w
        return series
