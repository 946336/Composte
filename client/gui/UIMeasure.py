
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsLineItem
from client.gui import UISettings
from client.gui.UINote import UINote

import music21

class UIMeasure(QtWidgets.QGraphicsItemGroup):

    __stafflinePen = QtGui.QPen(QtGui.QBrush(Qt.black), 1, Qt.SolidLine, Qt.FlatCap)
    __barlinePen = QtGui.QPen(QtGui.QBrush(Qt.black), 2, Qt.SolidLine, Qt.FlatCap)

    def __init__(self, scene, width, clef, keysig, timesig,
                 newClef = False, newKeysig = False, newTimesig = False,
                 forceDrawClef = False, *args, **kwargs):
        super(UIMeasure, self).__init__(*args, **kwargs)
        self.__scene = scene
        self.__width = width

        self.__clef = clef
        self.__newClef = False
        self.__keysig = keysig
        self.__newKeysig = False
        self.__timesig = timesig
        self.__newTimesig = False

        self.__baseObjs = []
        self.__noteObjs = {}

        self.__initGraphics()

    def __initGraphics(self):
        for i in range(0,5):
            line = QGraphicsLineItem(0, 2 * i * UISettings.PITCH_LINE_SEP,
                                     self.__width, 2 * i * UISettings.PITCH_LINE_SEP,
                                     self)
            line.setPen(self.__stafflinePen)
            self.__baseObjs.append(line)

        barline = QGraphicsLineItem(0, 0, 0, 4 * 2 * UISettings.PITCH_LINE_SEP + 1, parent=self)
        barline.setPen(self.__barlinePen)
        self.__baseObjs.append(barline)
        barline = QGraphicsLineItem(self.__width, 0,
                                    self.__width, 4 * 2 * UISettings.PITCH_LINE_SEP + 1, parent=self)
        barline.setPen(self.__barlinePen)
        self.__baseObjs.append(barline)

    def __redraw(self):
        """
        Redraw all graphics objects, moving them to update as necessary, e.g.
        after a resize.
        """
        ## TODO: This is a terrible way of doing this, we could reuse the old
        ##   objects rather than destroying them and creating new ones.
        notes = list(self.__noteObjs.keys())
        for item in self.__noteObjs.values():
            self.__scene.removeItem(item)
        self.__noteObjs.clear()
        for item in self.__baseObjs:
            self.__scene.removeItem(item)
        self.__baseObjs.clear()

        self.__initGraphics()
        for note in notes:
            self.addNote(*note)

    def addNote(self, pitch, ntype, offset):
        note = ntype(parent = self)
        if offset + note.length() > self.length():
            raise ValueError("Note extends past end of measure")
        if (pitch, ntype, offset) in self.__noteObjs:
            raise ValueError("Note already exists")
        self.__noteObjs[(pitch, ntype, offset)] = note

        notesWidth = (self.__width
                        - UISettings.BARLINE_FRONT_PAD
                        - UISettings.BARLINE_REAR_PAD )
        note_x = (UISettings.BARLINE_FRONT_PAD
                    + notesWidth * (offset / (self.length() - 1)))
        note_y = (8 * UISettings.PITCH_LINE_SEP
                    - self.clef().position(pitch) * UISettings.PITCH_LINE_SEP)
        note.setPos(note_x, note_y)


    def delNote(self, pitch: music21.pitch.Pitch,
                ntype: UINote, offset: float):
        if (pitch, ntype, offset) not in self.__noteObjs:
            raise ValueError("Deleting nonexistent note")
        self.__scene.removeItem(self.__noteObjs[(pitch, ntype, offset)])
        del self.__noteObjs[(pitch, ntype, offset)]

    def clef(self):
        return self.__clef
    def keysig(self):
        return self.__keysig
    def timesig(self):
        return self.__timesig
    def width(self):
        return self.__width

    def setClef(self, clef, newClef = True):
        self.__clef = clef
        self.__newClef = newClef
    def setKeysig(self, keysig, newKeysig = True):
        self.__keysig = keysig
        self.__newKeysig = newKeysig
    def setTimesig(self, timesig, newTimesig = True):
        self.__timesig = timesig
        self.__newTimesig = newTimesig
    def setWidth(self, width):
        self.__width = width
        self.__redraw()

    def length(self):
        return self.__timesig.measureLength()
