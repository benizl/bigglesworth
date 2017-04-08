#!/usr/bin/env python

from biggles import *

system = System("Sol Invictus")
user = User("Driver")

race_requirements = ExternalRequirementSet()

width_constraint = Constraint("shall have a maximum width less than 2000mm", width__lte = "2000mm")
panel_area_constraint = Constraint("shall have a total solar panel area less than 4m2", panel_area__lte = "4m2")

safety_requirement = ExternalRequirement("shall provide adequte protection to the driver in the event of an accident")
occupant_cell_requirement = DerivedRequirement(safety_requirement, "shall provide an occupant cell capable of withstanding 10N lateral force", occupant_cell_lateral_force__gte="10N")
light_requirement = DerivedRequirement(safety_requirement, "shall provide brake lights", brake_lights__eq="True")

race_requirements.add(width_constraint)
race_requirements.add(panel_area_constraint)
race_requirements.add(safety_requirement)

advertising_requirement = Requirement("shall provide adequate vertical surface area for sponsor logos", side_area__gte="2m2")

ui = user.interfaces_with(system, name="user interface")

chassis = Subsystem("chassis", system)
aero = Subsystem("aero", system)
control = Subsystem("control", system)
power = Subsystem("power", system)

chassis.interfaces_with(aero)
chassis.interfaces_with(power)

power.interfaces_with(control)

race_requirements.allocate_to(system)
advertising_requirement.allocate_to(system)

chassis_design = Design("Chassis Design")
chassis_design.add_property(width="max children")
chassis_design.add_property(length="front frame length + interconnector length + rear frame length")
chassis_design.add_property(mass="sum children")
chassis_design.implements(chassis)

front_frame = Subsystem("front frame", chassis)
front_frame_design = Design("Front Frame Design")
front_frame_design.add_property(mass="20kg")
front_frame_design.add_property(width="1900mm")

front_frame_design.implements(front_frame)

rear_frame = Subsystem("rear frame", chassis)
rear_frame_design = Design("Rear Frame Design")
rear_frame_design.add_property(mass="20kg")
rear_frame_design.add_property(width="2100mm")

rear_frame_design.implements(rear_frame)

interconnector = Subsystem("interconnector", chassis)
interconnector.interfaces_with(front_frame)
interconnector.interfaces_with(rear_frame)
interconnector_design = Design("Interconnector Design")
interconnector_design.add_property(mass="5kg")
interconnector_design.add_property(length="2000mm")
interconnector_design.add_property(occupant_cell_lateral_force="5N")

interconnector_design.implements(interconnector)

aero_design = Design("Aero Design")
aero_design.implements(aero)
aero_design.add_property(width="chassis.width + 100mm")
aero_design.add_property(length="chassis.length + 200mm")
aero_design.add_property(height="chassis.height + 150mm")
aero_design.add_property(top_area="width * length")
aero_design.add_property(side_area="length * height")
aero_design.add_property(panel_area="4m2")

print(aero_design.get_property('width'))

system_design = Design("System Design")
system_design.add_property(width="max children")
system_design.add_property(mass="sum children")
system_design.add_property(panel_area="aero.panel_area")

system_design.implements(system)

occupant_cell_requirement.allocate_to(chassis)
occupant_cell_requirement.allocate_to(interconnector)

light_requirement.allocate_to(control)

control_design = Design("Control")
control_design.implements(control)
control_design.add_property(brake_lights=True)

prettyprint_verification(system.verify())

#prettyprint_verification(system.verify())

