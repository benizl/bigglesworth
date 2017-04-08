#!/usr/bin/env python3

from pint import UnitRegistry
ur = UnitRegistry()

from modgrammar import *
grammar_whitespace_mode = "optional"

class Variable(Grammar):
	grammar = ONE_OR_MORE(WORD("a-zA-Z", "a-zA-Z0-9"))

class UnitValue(Grammar):
	grammar_whitespace_mode = "explicit"
	grammar = (WORD("0-9."), OPTIONAL(WORD("a-zA-Z"), OPTIONAL(WORD("[0-9]"))))

class UncertainValue(Grammar):
	grammar = (UnitValue, OPTIONAL(L("+/-") | L("+-"), UnitValue))

class ParenTerm(Grammar):
	grammar = ("(", REF("Expression"), ")")

class Term(Grammar):
	grammar = (UncertainValue | ParenTerm | Variable)

class Product(Grammar):
	grammar = (Term, ZERO_OR_MORE((L("*") | L("/"), Term)))

class Sum(Grammar):
	grammar = (Product, ZERO_OR_MORE((L("+") | L("-"), Product)))

class Expression(Grammar):
	grammar = Sum

def process(tree):
	if isinstance(tree, Expression):
		return process(tree[0])
	elif isinstance(tree, Sum):
		result = process(tree[0])

		for g in tree[1]:
			term = process(g[1])
			if g[0] == '-':
				term *= -1

			result += term

		return result
	elif isinstance(tree, Product):
		result = process(tree[0])

		for g in tree[1]:
			term = process(g[1])
			if g[0] == '/':
				term = 1 / term

			result *= term

		return result
	elif isinstance(tree, Term):
		return process(tree[0])
	elif isinstance(tree, ParenTerm):
		return process(tree[1])
	elif isinstance(tree, UncertainValue):
		lhs = process(tree[0])
		if tree[1] is None:
			return lhs
		else:
			# Drop the "+/-"
			err = process(tree[1][1])

			# If only one of the mag or err has units specified, use that
			# for both, e.g. 1m +/- 0.1 is valid and means +/- 0.1m
			if err.units == ur.dimensionless:
				err = err.magnitude * lhs.units
			elif lhs.units == ur.dimensionless:
				lhs = lhs.magnitude * err.units

			return lhs.plus_minus(err)
	elif isinstance(tree, Variable):
		ws = [ w.string for w in tree[0]]
		obj = "_".join(ws[:-1])
		attr = ws[-1]

		if obj:
			return getattr(globals()[obj], attr)
		else:
			return globals()[attr]
	elif isinstance(tree, UnitValue):
		try:
			val = float(tree[0].string)
		except ValueError:
			try:
				val = int(tree[0].string, 0)
			except ValueError:
				raise
		if tree[1] is None:
			unit = ur.dimensionless
		else:
			unit = getattr(ur, tree[1][0].string)
			if tree[1][1] is not None:
				unit = unit**int(tree[1][1].string)

		return val * unit

tv1 = 8

class Thing(object):
	pass

tv2 = Thing()
tv2.atb = 9

parser = Expression.parser()
result = parser.parse_text("5+2*3", eof=True)
print(process(result))
