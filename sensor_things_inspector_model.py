'''
Created on 25 nov 2024

@author: MRTSDR71E
'''

from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QStyledItemDelegate, QSpinBox

# 
#-----------------------------------------------------------
class LimitDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        val = index.data()
        option.text = str(val)
        option.displayAlignment = Qt.AlignVCenter | Qt.AlignRight

    def createEditor(self, parent, option, index):
        editor = QSpinBox(parent)
        editor.setMinimum(1)
        editor.setMaximum(1000000)
        return editor
    

    
# 
#-----------------------------------------------------------
class InspectorLimitModel(QAbstractTableModel):
    def __init__(self, data: list):
        super().__init__()
        
        self._data = []
        
        if isinstance(data, list):
            for rec in data:
                if isinstance(rec, dict) and 'Name' in rec:
                    new_rec = {
                        'Name' : rec.get('Name', '???'),
                        'Value': rec.get('Value', 0),
                        'Description': rec.get('Description', ''),
                        'DisplayName': rec.get('DisplayName', ''),
                    }
                    
                    self._data.append(new_rec)
  
    def setLimit(self, name, value):
        if not name:
            return
        
        if not isinstance(value, int):
            return
            
        if value < 1:
            return
            
        for rec in self._data:
            if rec.get('Name') == str(name):
                rec['Value'] = value
                return
            
    def getLimit(self, name):
        if not name:
            return
        
        for rec in self._data:
            if rec.get('Name') == str(name):
                return rec['Value']
            
        return 1    
        
    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return 3
        
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
            
        if index.column() != 1:
            return Qt.ItemIsEnabled
            
        # add editable flag
        return super().flags(index) | Qt.ItemIsEditable

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal:
            # column header text
            if role == Qt.DisplayRole:
                if col == 0:
                    return self.tr("Entity")
                elif col == 1:
                    return self.tr("Limit")
                #elif col == 2:
                #    return self.tr("Description")
                else:
                    return ''

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            rec = self._data[index.row()]
            if index.column() == 0:
                return rec.get('DisplayName', rec.get('Name'))
            return list(rec.values())[index.column()]
            
        elif role == Qt.EditRole:
            self._editing = True
            rec = self._data[index.row()]
            return list(rec.values())[index.column()]
            
        elif role == Qt.FontRole:
            if index.column() == 0:
                font = QFont()
                font.setBold(True)
                return font
                
        elif role == Qt.TextAlignmentRole:
            if index.column() == 1:
                return Qt.AlignRight | Qt.AlignVCenter
        
        elif role == Qt.ToolTipRole:
            if index.column() == 2:
                rec = self._data[index.row()]
                return list(rec.values())[index.column()]
            
        return None
        
    def setData(self, index, value, role):
        if role == Qt.EditRole:
            # Set parameter value
            if index.column() == 1:
                rec = self._data[index.row()]
                rec['Value'] = value
                return True
        return False


