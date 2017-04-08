
import pytest

import pint.errors
from pint import UnitRegistry
from uncertainties import ufloat
ur = UnitRegistry()

from textx.metamodel import metamodel_from_file

def re_process(string, _locals=None):
	import re

	def sub_units(match):
		try:
			unit = getattr(ur, match.groups()[2])
			return ur"{0}({1}*ur.{2})".format(*match.groups())
		except (ValueError, pint.errors.UndefinedUnitError):
			return ur"{0}{1}{2}".format(*match.groups())

	# Sub units with unit objects, e.g.  12mm -> (12*ur.mm)
	string = re.sub(ur"(\A|[* +-/(]+)(\d+)(\w+)", sub_units, string)

	# Anything still unitless, attach "counts" units so all numbers are consistent
	string = re.sub(ur"(\A|[^\w])(\d+)(?!\d|\*ur)", ur"\1(\2*ur.counts)", string)

	# Sub +/- with plus_minus operator (now that all numbers are pint.Quantity)
	string = re.sub(ur"(\(\d+\*ur\.\w+\))\s*\+/-\s*(\(\d+\*ur\.\w+\))", ur"\1.plus_minus(\2)", string)

	# Convert space-separated identifiers to period-separated, e.g. "chassis width" -> "chassis.width"
	string = re.sub(ur"(\w) (\w)", ur"\1.\2", string)

	return eval(string, globals(), _locals)


def modgrammar_process(string):
	mm = metamodel_from_file('biggles_requirement.tx')



class Param(object):
	def __getattribute__(self, attr):
		p = super(Param, self).__getattribute__(attr)
		if not isinstance(p, basestring) or p[0] == "'":
			return p

		return process(p)


def test_f0():
	assert(process("12mm") == 12 * ur.mm)
	assert(process("12mm + 1cm") == 2.2 * ur.cm)
	assert(process("12 + 1") == 13 * ur.counts)

	t = process("12+/-1")
	assert(t.value == 12*ur.counts and t.error == 1*ur.count)

	t = process("12mm +/- 1cm")
	assert(t.value == 12 * ur.mm and t.error == 1 * ur.cm)


def test_f1():
	chassis = Param()
	chassis.width = "1000mm"

	test1 = "chassis width + 100mm"

	assert(process(test1, locals()) == 1.1 * ur.m)

def test_f2():
	test2 = "200cm+/-10mm"
	t = process(test2)
	assert(t.value == 200 * ur.cm and t.error == 10 * ur.mm)

def test_f3():
	test3 = "400cm+/-20cm - 2m"
	t = process(test3)
	assert(t.value == 2 * ur.m and t.error == 20 * ur.cm)


if __name__ == '__main__':
	pytest.main(['-x', __file__])

