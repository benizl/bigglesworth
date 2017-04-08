import re 

class BigglesException(Exception): pass
class SystemDefinitionException(BigglesException): pass
class OperationException(BigglesException): pass
class VerificationException(BigglesException): pass

unit_conversions = {
	'mm'	: 0.001,
	'm'		: 1,
	'N'		: 1,
	'kg'	: 1,
	'm2'	: 1
}

def prettyprint_verification(results):
	for result in results:
		print str(result)


def _normalise_property(prop):
	if not isinstance(prop, basestring):
		return prop

	if prop.lower() == 'true': return True
	if prop.lower() == 'false': return False

	try:
		return float(prop)
	except ValueError:
		pass

	try:
		val, units = re.match("(\d+)(.*)", prop).groups()
		val = float(val) * unit_conversions[units]
		return val
	except AttributeError, TypeError:
		raise VerificationException("Can't interpret property {}".format(prop))

def _find_and_normalise(prop, owner, scope):
	if not isinstance(prop, basestring):
		return prop

	if '.' in prop:
		obj_name, prop = prop.split('.')

		for obj in scope:
			if obj.name == obj_name and obj.design is not None:
				val = obj.design.get_property(prop)
				print("Found property '{}' = '{}' in subsystem '{}'".format(prop, val, obj_name))
				break
		else:
			raise VerificationException("Can't find named object '{}' looking for property '{}'".format(obj_name, prop))
	else:
		val = prop
		print("Property '{}' = '{}' found in owner '{}'".format(prop, val, owner))

	return _normalise_property(val)

def _collect_remotes(owner, interfaces):
	remotes = set()
	for inter in interfaces:
		remotes = remotes | set(inter.systems)

	remotes = remotes - set([owner])

	return list(remotes)

def _verify_parameter(actual, operation, literal):
	import re

	try:
		act = _normalise_property(actual)
		lit = _normalise_property(literal)
	except AttributeError, TypeError:
		raise VerificationException("Can't interpret literals {}/{}".format(actual, literal))

	if operation == "eq":		return act == lit
	elif operation == "lt":		return act <  lit
	elif operation == "lte":	return act <= lit
	elif operation == "gt":		return act >  lit
	elif operation == "gte":	return act >= lit
	else:
		raise VerificationException("Unknown operation {}".format(operation))



class VerificationResult():
	INFO = "Information"
	WARN = "Warning"
	ERROR = "Error"

	def __init__(self, owner, severity, message):
		self.severity = severity
		self.message = message
		self.owner = owner

	def __str__(self):
		return "{severity:<16}{message} ({owner})".format(owner=self.owner, severity=self.severity, message=self.message)

	def __repr__(self):
		return "VerificationResult[{}]".format(str(self))

class Subsystem(object):
	def __init__(self, name, parent):
		self.name = name
		self.parent = parent
		self.children = []
		self.design = None
		self.requirements = []
		self.interfaces = []

		if self.parent:
			self.parent.children.append(self)

	def __str__(self):
		return 'Subsytem "{}"'.format(self.name)

	def __repr__(self):
		return str(self)

	def verify(self):
		responses = []

		if not len(self.requirements):
			responses.append(VerificationResult(self, VerificationResult.WARN, "System has not been allocated any requirements"))

		for requirement in self.requirements:
			responses.extend(requirement.verify())

		for child in self.children:
			responses.extend(child.verify())

		return responses

	def interfaces_with(self, subsystem, name=None):
		if name is None:
			name = "{} <-> {}".format(self.name, subsystem.name)

		i = Interface(name, self, subsystem)
		self.interfaces.append(i)
		subsystem.interfaces.append(i)

		return i


# System works the same as subsystem except that there can only be one of them and they don't have a parent
class System(Subsystem):
	_inst = None

	def __init__(self, *args, **kwargs):
		if System._inst is not None:
			raise SystemDefinitionException("Only one System may be defined")

		System._inst = self

		super(System, self).__init__(parent=None, *args, **kwargs)


	def __str__(self):
		return 'System "{}"'.format(self.name)


	def verify(self):
		responses = []

		if not len(self.children):
			responses.append(VerificationResult(self, VerificationResult.WARN, "System has no children"))

		responses.extend(super(System, self).verify())

		return responses


# User is just another subsystem but doesn't have to belong to the heirarchy
class User(Subsystem):
	def __init__(self, name):
		super(User, self).__init__(name, parent=None)

	def __str__(self):
		return 'User "{}"'.format(self.name)

	def __repr__(self):
		return str(self)


class Design(object):
	def __init__(self, name):
		self.properties = {}
		self.name = name
		self.subsystem = None

	def __str__(self):
		return 'Design "{name}" [implementing {subsys} with {props}]'.format(name=self.name, subsys=self.subsystem, props=self.properties)

	def __repr__(self):
		return 'Design "{name}" [implementing {subsys}]'.format(name=self.name, subsys=self.subsystem)

	def __getitem__(self, item):
		if item not in self.properties:
			return super(Design, self).__getitem__(self, item)

		prop = self.properties[item]

		if not isinstance(prop, basestring):
			return prop

		els = prop.split(' ')
		out = []
		for el in els:
			for unit in unit_conversions:
				if el.endswith(unit):
					el = '({}*{})'.format(el, unit_conversions[unit])
					break
			out.append(el)

		eval_str = ' '.join(out)
		


	def add_property(self, **properties):
		# I'm sure there's a better way to take the union of two dicts..
		self.properties = dict(self.properties.items() + properties.items())

	def get_property(self, prop):

		if not prop in self.properties:
			return None

		if not self.subsystem:
			raise VerificationException("Trying to verify design {} but is not linked to subsystem".format(self))

		try:
			return _normalise_property(self.properties[prop])
		except VerificationException:
			pass # If the property can't be interpretted directly, it's likely in need of dynamic calculation

		try:
			return _find_and_normalise(self.properties[prop], self, self.subsystem.children + _collect_remotes(self, self.subsystem.interfaces))
		except VerificationException:
			pass # If the property can't be interpretted directly, it's likely in need of dynamic calculation


		try:
			terms = self.properties[prop].split(' ')

			if len(terms) == 2:
				op, scope = terms

				if scope == 'children':
					props = [ _normalise_property(child.design.get_property(prop))
						for child in self.subsystem.children
						if child.design is not None and child.design.get_property(prop) is not None ]
				elif scope == 'interfaces':
					remotes = _collect_remotes(self, self.subsystem.interfaces)
					props = [ _normalise_property(remote.design.get_property(prop))
						for remote in remotes
						if remote.design is not None and remote.design.get_property(prop) is not None ]
				else:
					raise VerificationException("Unknown dynamic property scope '{}'".format(scope))

				if not len(props):
					raise VerificationException("Can't find property '{}' in any objects in scope '{}'".format(prop, scope))

				if op == 'max':
					return max(props)
				elif op == 'sum':
					return sum(props)
			elif len(terms) == 3:
				print(terms)
				term1, op, term2 = terms

				term1 = _find_and_normalise(term1, self, self.subsystem.children + _collect_remotes(self, self.subsystem.interfaces))
				term2 = _find_and_normalise(term2, self, self.subsystem.children + _collect_remotes(self, self.subsystem.interfaces))
				print(term1, op, term2)
				if op == '+': return term1 + term2
				elif op == '-': return term1 - term2
				elif op == '*': return term1 * term2
				elif op == '/': return term1 / term2
				else:
					raise VerificationException("Unknown operation '{}' in calculation '{}'".format(op, terms))
			else:
				raise VerificationException("Can't interpret property string '{}' for design '{}'".format(prop, self))

		except ValueError, TypeError:
			raise VerificationException("Can't work out how to get property '{}' for design '{}'".format(prop, self))

	def implements(self, subsystem):
		self.subsystem = subsystem
		self.subsystem.design = self


class Interface(object):
	def __init__(self, name, *systems):
		if len(systems) < 2:
			raise SystemDefinitionException("Tried to create an interface between fewer than two things")
		self.systems = systems
		self.name = name
		self.requirements = []

	def __str__(self):
		return 'Interface "{}"'.format(self.name)

	def __repr__(self):
		return str(self)

class Requirement(object):
	def __init__(self, text, **parametrics):
		self.allocated_to = None
		self.text = text
		self.children = []

		if len(parametrics) == 0:
			self.parameter = None
		elif len(parametrics) == 1:
			parameter_item = parametrics.items()[0]
			parameter, operation = parameter_item[0].split('__')
			#parameter = parameter.replace("_", " ")
			self.parameter = (parameter, operation, parameter_item[1])
		else:
			raise SystemDefinitionException("Can't have a single requirement with multiple parametric constraints, try building derived requirements")

	def __str__(self):
		return 'Requirement "The {} {}"'.format(self.allocated_to, self.text)

	def __repr__(self):
		return str(self)

	def allocate_to(self, thing):
		if isinstance(thing, Subsystem):
			if self.allocated_to is not None and self.allocated_to != thing.parent:
				raise SystemDefinitionException("Tried to re-allocate a requirement to something other than a child of the existing owner")
		elif isinstance(thing, Interface):
			if self.allocated_to is not None and not self.allocated_to in thing.systems:
				raise SystemDefinitionException("Tried to re-allocate a requirement to an interface not connected to the existing owner")
		else:
			raise SystemDefinitionException("Tried to allocate a requirement to something other than a System/Subsystem/Interface")

		if self.allocated_to is not None:
			self.allocated_to.requirements.remove(self)

		thing.requirements.append(self)
		self.allocated_to = thing

		# Recursively allocate all derived requirements too
		for child in self.children:
			child.allocate_to(thing)

	def parent_of(self, requirement):
		self.children.append(requirement)

	def verify(self):
		responses = []

		if not self.allocated_to:
			responses.append(VerificationResult(self, VerificationResult.INFO, "Requirement isn't allocated to anything"))

		if self.parameter is None and not len(self.children):
			responses.append(VerificationResult(self, VerificationResult.WARN, "Requirement isn't itself verifiable and has no requirements derived from it"))

		if self.parameter is not None:
			if self.allocated_to is None:
				responses.append(VerificationResult(self, VerificationResult.WARN, "Requirement has a parametric test but isn't bound to a subsystem to test against"))
			else:
				parameter, operation, literal = self.parameter
				design = self.allocated_to.design

				if design is None:
					responses.append(VerificationResult(self, VerificationResult.WARN, "Parametric design can't be verified because there's no implementing design attached"))
				else:
					actual_value = design.get_property(parameter)

					passed = _verify_parameter(actual_value, operation, literal)

					if passed:
						responses.append(VerificationResult(self, VerificationResult.INFO, "Requirement passed: {} {} {}".format(actual_value, operation, literal)))
					else:
						responses.append(VerificationResult(self, VerificationResult.ERROR, "Requirement failed: {} {} {}".format(actual_value, operation, literal)))

		for child in self.children:
			responses.extend(child.verify())

		return responses


# Does this need to be a separate thing?
class ExternalRequirement(Requirement):
	pass

class Constraint(Requirement):
	pass

class DerivedRequirement(Requirement):
	def __init__(self, parent, *args, **kwargs):
		self.parent = parent
		parent.parent_of(self)
		super(DerivedRequirement, self).__init__(*args, **kwargs)

class RequirementSet(object):
	def __init__(self):
		self.requirements = []
		self.allocated = False

	def add(self, requirement):
		if not isinstance(requirement, Requirement):
			raise SystemDefinitionException("Trying to add a non-requirement to a requirement set")

		if self.allocated:
			raise OperationException("Can't add new requirements to a set once you've allocated them")

		self.requirements.append(requirement)

	def allocate_to(self, subsystem):
		if self.allocated:
			raise OperationException("Can't allocate a requirement set twice")

		for requirement in self.requirements:
			requirement.allocate_to(subsystem)

		self.allocated = True

class ExternalRequirementSet(RequirementSet):
	pass
