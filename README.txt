*********************************************************
Python framework for generating AWS CloudFormation stacks
*********************************************************

Changes
*******

0.6.0 (2014-08-14)
==================

- Allow region_name argument to stack_region to constrain find_stack.

0.5.1 (2013-11-21)
==================

Fixed: creating stack failed due to a bug in querying for existing stacks.

0.5.0 (2013-11-20)
==================

- Added a ``create_only`` flag to the ``upload`` function to prevent
  stack updates.

- Added an ``attr`` helper function for creating resource-attribute
  references.

- Added a stack ``resource(name, type, **options)`` method for more
  compactly defining stack resources.

0.4.0 (2012-11-20)
==================

???

0.3.0 (2012-11-09)
==================

- Added functions for finding getting stacks and determing stack regions

0.1.0 (2012-??-??)
==================

Initial release
