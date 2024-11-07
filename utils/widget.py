# -*- coding: utf-8 -*-
"""Qt Widgets utility class

Description
-----------

Utility class for URL.

Libraries/Modules
-----------------

- None.
    
Notes
-----

- None.

Author(s)
---------

- Created by Sandro Moretti on 06/06/2022.
  Dedagroup Spa.

Members
-------
"""

class QtWidgetUtils: 
    
    @staticmethod
    def getParentWidgetOfType(widget, of_type):
        """Find parent widget of specific type"""
        while widget is not None:
            if type(widget) == of_type:
                break
            widget = widget.parent()
        return widget
    
    