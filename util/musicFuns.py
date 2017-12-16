import music21
import copy

# TODO
# Refactor projects and streams globally to obey a
# Score > Part > Measure hierarchy
# END TODO

# The server always needs to know WHERE to make
# an update, and needs to send that information
# to all connected clients. Thus, the offset from
# the beginning of the piece (in quarterLengths, or "qLs")
# must always be given as the first argument to all
# update functions. Also, the server must know WHICH
# part to apply the update in, hence the need to
# pass it as the second argument in all cases.

# Since rests are simply portions of the music where
# no sound is made, they do not need to be explicitly
# notated in the backend representation.

# Though music21 allows explicit definitions of which
# 8th/16th notes (and below) should be beamed together
# into a single unit, this is wildly unnecessary for
# our application. Correct beaming would be the job of
# the GUI, and our GUI may not even address beaming whatsoever.
# Likewise, for this initial implemenation, articulations,
# expressions, and repeats remain unimplemented.

def changeKeySignature(offset, part, newSigSharps):
    """ Changes the Key Signature at a given offset inside a part.
        Must provide the correct number of sharps in the key signature
        as an integer. Negative numbers correspond to the number of flats. """
    newKeySig = music21.key.KeySignature(newSigSharps)
    oldKeySigs = part.getKeySignatures()
    for i in range(len(oldKeySigs)):
        if oldKeySigs[i].offset == offset:
            part.replace(oldKeySigs[i], newKeySig)
            if i + 1 == len(oldKeySigs):
                renameNotes(offset, part, newKeySig)
                return [offset, part.highestTime]
            else:
                renameNotes(offset, part, newKeySig, oldKeySigs[i + 1].offset)
                return [offset, oldKeySigs[i + 1].offset]
    part.insert(offset, newKeySig)
    for oldKeySig in oldKeySigs:
        # oldKeySigs is sorted, so this finds the first oldKeySig
        # That's after the one that was just inserted
        if offset < oldKeySig.offset:
            renameNotes(offset, part, newKeySig, oldKeySig.offset)
            return [offset, oldKeySig.offset]
    renameNotes(offset, part, newKeySig)
    return [offset, part.highestTime]

def renameNotes(startOffset, part, keySig, endOffset=None):
    """ Rename all notes affected by a key signature change
        intelligently so as to not have sharp accidentals
        in a flat key signature. Diffs need to accumulate
        while the renaming is in process. """
    notes = part.notes
    hasSharps = 0 < keySig.sharps
    for note in notes:
        offset = note.offset
        if endOffset is None:
            if startOffset <= offset:
                part.replace(note, renameNote(note, hasSharps))
        else:
            if startOffset <= offset and offset <= endOffset:
                part.replace(note, renameNote(note, hasSharps))

def renameNote(note, hasSharps):
    """ Rename a note intelligently within a key. """
    # Have to create a NEW Note object to use replace. Reasons unclear.
    name = note.name
    octave = note.octave
    duration = note.duration
    if hasSharps:
        if name[1] == '-':
            noteName = name[0]
            if noteName == 'A':
                newName = 'G'
            else:
                newName = chr(ord(noteName) - 1)
            newName += '#'
        else:
            newName = name
    else:
        if name[1] == '#':
            noteName = name[0]
            if noteName == 'G':
                newName = 'A'
            else:
                newName = chr(ord(noteName) + 1)
            newName += '-'
        else:
            newName = name
    return createNote(newName + str(octave), duration.quarterLength)

# NOT IN MINIMUM DELIVERABLE
def changeTimeSignature(offset, part, newSigStr):
    """ Changes the Time Signature at a given offset inside a part.
        newTimeSig must be a string representing the new time signature,
        such as '4/4' or '6/8'. """
    newTimeSig = music21.meter.TimeSignature(newSigStr)
    oldTimeSigs = part.getTimeSignatures()
    for oldTimeSig in oldTimeSigs:
        if oldTimeSig.offset == offset:
            part.replace(oldTimeSig, newTimeSig)
            return part.getElementsByOffset(offset)
    part.insert(offset, newTimeSig)
    return part.getElementsByOffset(offset)

def insertMetronomeMark(offset, score, bpm):
    """ Insert a metronome marking in a list of
        parts at a given offset. The constructor needs 
        staff text as a string (empty for our purposes), pulses per 
        minute as an integer, and the duration in quarterLengths 
        of a single pulse as a float. Since duration 
        is 1.0, the second argument is exactly equivalent to 
        BPM (beats per minute). """
    mark = music21.tempo.MetronomeMark("", bpm, 1.0)
    for part in score:
        markings = part.metronomeMarkBoundaries()
        markFound = False
        for marking in markings:
            # Marking already exists at that location, so update it
            if marking[0] == offset:
                markFound = True
                part.replace(marking[2], mark)
                break
        if markFound: 
            continue
        part.insert(offset, mark)
    return [offset, offset]

def removeMetronomeMark(offset, parts):
    """ Remove a metronome marking from each part in
        a list of parts at a given offset. """
    for part in parts:
        markings = part.metronomeMarkBoundaries()
        for marking in markings:
            if marking[0] == offset and offset != 0.0:
                part.remove(marking[2])
    return [offset, offset]

def createNote(pitchName, durationInQLs):
    """ Creates a Note from the name of a pitch (as a string)
        and a duration in quarter lengths (as a float). """
    note = music21.note.Note(pitchName)
    note.duration = music21.duration.Duration(durationInQLs)
    note.pitch.spellingIsInferred = False
    # Needed in order to sever ties between notes
    note.tiePartners = [None, None]
    return note

def createRest(durationInQLs): 
    """ Creates a Rest of a given duration. Useful for the 
        GUI, but unimportant for things like playback. """
    rest = music21.note.Rest()
    rest.duration = music21.duration.Duration(durationInQLs)
    return rest

def insertRest(offset, part, duration): 
    """ Insert a rest of a given duration into a part
        at a given offset. """
    rest = createRest(duration)

def insertNote(offset, part, pitchStr, duration):
    """ Add a note at a given offset to a part. """
    newNote = createNote(pitchStr, duration)
    bounds = (offset, offset + duration) 
    notes = part.notes
    maxLims = [None, None]
    for note in notes: 
        limits = (note.offset, 
                  note.duration.quarterLength + note.offset)          
        if bounds[0] < limits[1] and limits[0] < bounds[1]:
            removeNote(note.offset, part, note.pitch.nameWithOctave)
            if maxLims[0] is None and maxLims[1] is None: 
                maxLims = [limits[0], limits[1]]
            else: 
                maxLims = [min(maxLims[0], limits[0]),
                           max(maxLims[1], limits[1])]
    if maxLims[0] is None and maxLims[1] is None: 
        maxLims = [bounds[0], bounds[1]]
    else: 
        maxLims = [min(maxLims[0], bounds[0]),
                   max(maxLims[1], bounds[1])]
    part.insert(offset, newNote)
    return maxLims

def removeNote(offset, part, removedNoteName):
    """ Remove a note at a given offset into a part. """
    notes = part.notes
    maxLims = [offset, offset]
    for note in notes:
        noteName = note.pitch.nameWithOctave
        if note.offset == offset and noteName == removedNoteName:
            if note.tiePartners[0] is not None: 
                maxLims[0] = note.tiePartners[0]
                updateTieStatus(note.tiePartners[0], part, noteName)
            if note.tiePartners[1] is not None: 
                maxLims[1] = note.tiePartners[1]
                updateTieStatus(offset, part, noteName)
            part.remove(note)
            return maxLims
    return maxLims

def updateTieStatus(offset, part, noteName):
    """ Updates the tie status of a note with the name noteName
        at a given offset into a given part. The offset given to
        this function MUST be the same as the offset of the
        FIRST note in a legally tie-able pair of notes (the notes
        must be the same pitch, and there must be no rests between them)."""
    notes = part.notes
    for note in notes:
        pitchStr = note.pitch.nameWithOctave
        if note.offset == offset and pitchStr == noteName:
            qL = note.duration.quarterLength
            tieCantidates = part.getElementsByOffset(note.offset + qL)
            for cantidate in tieCantidates:
                if cantidate.pitch.nameWithOctave == noteName:
                    makeTieUpdate([note, cantidate])
                else:
                    pass
            return [offset, note.offset + qL]
    return [offset, offset]

def makeTieUpdate(notes):
    """ If the pair of notes passed to this function is untied,
        this function ties them together. If ther pair of notes
        passed to this function is tied, the tie is severed. """
    [firstNote, secondNote] = notes
    # Add Ties
    if firstNote.tie is None and secondNote.tie is None:
        firstNote.tiePartners[1] = secondNote.offset
        secondNote.tiePartners[0] = firstNote.offset
        firstNote.tie = music21.tie.Tie("start")
        secondNote.tie = music21.tie.Tie("stop")
    elif firstNote.tie.type == "stop" and secondNote.tie is None:
        firstNote.tiePartners[1] = secondNote.offset
        secondNote.tiePartners[0] = firstNote.offset
        firstNote.tie.type = "continue"
        secondNote.tie = music21.tie.Tie("stop")
    elif firstNote.tie is None and secondNote.tie.type == "start":
        firstNote.tiePartners[1] = secondNote.offset
        secondNote.tiePartners[0] = firstNote.offset
        firstNote.tie = music21.tie.Tie("start")
        secondNote.tie.type = "continue"
    elif firstNote.tie.type == "stop" and secondNote.tie.type == "start":
        firstNote.tiePartners[1] = secondNote.offset
        secondNote.tiePartners[0] = firstNote.offset
        firstNote.tie.type = "continue"
        secondNote.tie.type = "continue"
    # Remove Ties
    elif firstNote.tie.type == "start" and secondNote.tie.type == "stop":
        firstNote.tiePartners[1] = None
        secondNote.tiePartners[0] = None
        firstNote.tie = None
        secondNote.tie = None
    elif firstNote.tie.type == "start" and secondNote.tie.type == "continue":
        firstNote.tiePartners[1] = None
        secondNote.tiePartners[0] = None
        firstNote.tie = None
        secondNote.tie.type = "start"
    elif firstNote.tie.type == "continue" and secondNote.tie.type == "continue":
        firstNote.tiePartners[1] = None
        secondNote.tiePartners[0] = None
        firstNote.tie.type = "stop"
        secondNote.tie.type = "start"
    elif firstNote.tie.type == "continue" and secondNote.tie.type == "stop":
        firstNote.tiePartners[1] = None
        secondNote.tiePartners[0] = None
        firstNote.tie.type = "stop"
        secondNote.tie = None
    # For completeness and defense against race conditions
    else:
        pass

def transpose(part, semitones):
    """ Transposes the whole part up or down
        by an integer number of semitones. """
    part = part.transpose(semitones)
    return [0.0, part.highestTime]

def insertClef(offset, part, clefStr):
    """ Inserts a new clef at a given offset in a given part.
        The types of clefs supported ON THE BACKEND are:
        'treble', 'treble8va', 'treble8vb, 'bass', 'bass8va',
        'bass8vb', 'frenchviolin', 'alto', 'tenor', 'cbaritone',
        'fbaritone', 'gsoprano', 'mezzosoprano', 'soprano',
        'percussion', and 'tab'. """
    newClef = music21.clef.clefFromString(clefStr)
    elems = part.getElementsByOffset(offset)
    # Only clef objects have an octaveChange field
    for elem in elems:
        if hasattr(elem, 'octaveChange'):
            part.replace(elem, newClef)
            return [offset, offset]
    part.insert(offset, newClef)
    return [offset, offset]

def removeClef(offset, part):
    """ Remove a clef from a given offset in a given part. """
    elems = part.getElementsByOffset(offset)
    for elem in elems:
        # Only clef objects have an octaveChange field
        if hasattr(elem, 'octaveChange'):
            if offset != 0.0:
                part.remove(elem)
            return [offset, offset]
    return [offset, offset]

def addInstrument(offset, part, instrumentStr):
    """ Given an instrument name, assigns that instrument
        to a part in the score. The number of instruments
        supported on the backend are much to numerous to name."""
    measure = measureAtOffset(offset, part) 
    measureOffset = offset - startOfNearestMeasure(offset, part)
    elems = measure.getElementsByOffset(measureOffset)
    instrument = music21.instrument.fromString(instrumentStr)
    for elem in elems:
        if hasattr(elem, 'instrumentName'):
            part.replace(elem, instrument)
            return [offset, offset]
    part.insert(offset, instrument)
    return [offset, offset]

def removeInstrument(offset, part):
    """ Remove an instrument beginning at offset from a given part. """
    measure = measureAtOffset(offset, part) 
    measureOffset = offset - startOfNearestMeasure(offset, part)
    elems = measure.getElementsByOffset(measureOffset)
    for elem in elems:
        if hasattr(elem, 'instrumentName'):
            measure.remove(elem)
            return [offset, offset]
    return [offset, offset]

def addDynamic(offset, part, dynamicStr):
    """ Adds a dynamic marking to a part at a given offset.
        Acceptable values of dynamicStr are 'ppp', 'pp', 'p',
        'mp', 'mf', 'f', 'ff', and 'fff'. """
    dynamic = music21.dynamics.Dynamic(dynamicStr)
    elems = part.getElementsByOffset(offset)
    for elem in elems:
        if hasattr(elem, 'volumeScalar'):
            part.replace(elem, dynamic)
            return [offset, offset]
    part.insert(offset, dynamic)
    return [offset, offset]

def removeDynamic(offset, part):
    """ Removes a dynamic marking from a part at a given offset. """
    elems = part.getElementsByOffset(offset)
    for elem in elems:
        if hasattr(elem, 'volumeScalar'):
            part.remove(elem)
            return [offset, offset]
    return [offset, offset]

def addLyric(offset, part, lyric):
    """ Add lyrics to a given note in the score. """
    notes = part.notes
    for note in notes:
        if note.offset == offset:
            note.addLyric(lyric)
            return [offset, offset]
    return [offset, offset]

def playback(score): 
    """ Playback the current project from the beginning 
        of a part. """
    music21.midi.realtime.StreamPlayer(score).play()    

def boundedOffset(part, bounds): 
    """ Returns a bounded offset list for GUI uses. 
        An offset map is an (element, offset, endTime) triple.
        element is the music21 object to insert.
        offset is the insertion offset of the music21 object. 
        endTime is the termination offset of the music21 object. """
    offs = part.offsetMap()
    return [x for x in offs 
            if bounds[0] <= x.offset and x.endTime < bounds[1]]

################## MEASURE HELPER FUNCTIONS ####################

def insertMeasures(offset, part, numToInsert): 
    """ Insert a number of measures at a given offset into a part. 
        If offset is in the middle of a measure, insertion begins
        at the end of the measure containing offset. """
    barLength = barDurationAtOffset(offset, part)
    offsetShift = barLength * numToInsert
    after = startOfMeasureContainingOffset(offset, part) + barLength
    part.shiftElements(offsetShift, startOffset=after)
    for i in range(0, numToInsert): 
        inserted = copy.deepcopy(measureAtOffset(offset, part))
        fullBarRest = createRest(barLength) # Overwrite all notes
        inserted.insert(0.0, fullBarRest)
        part.insert(after, inserted) 
        after += barLength

def removeMeasures(startOffset, part, endOffset):
    """ Remove measures spanning from the beginning of 
        the measure containing start offset to the 
        end of the measure containing the end offset. """
    offs = part.offsetMap() 
    for off in offs: 
        if off[1] <= startOffset and off[2] < startOffset:
            begin = off[1]
        if off[1] < endOffset and off[2] <= endOffset: 
            end = off[2]
    for off in offs: 
        if begin <= off[1] and off[1] < end:
            part.remove(off[0])
    shift = begin - end
    part.shiftElements(shift, startOffset=end)
    
def appendMeasuresUpToOffset(offset, part): 
    """ Append measures on the end of a part until offset
        is contained within the span of the measures. """
    endOfStream = part.offsetMap()[-1][2]
    while endOfStream <= offset: 
        appendMeasure(part)
        endOfStream = part.offsetMap()[-1][2]

def appendMeasure(part):
    """ Append a single empty measure on the end of a part. """
    endOfStream = part.offsetMap()[-1][2]
    appended = copy.deepcopy(measureBeforeOffset(endOfStream, part))
    barLength = inserted.barDuration
    fullBarRest = createRest(barLength) # Overwrite all notes
    appended.insert(0.0, fullBarRest)
    part.append(appended)

def measureBeforeOffset(offset, part): 
    """ Find the measure before the measure containing 
        the given offset inside a part. """
    offs = part.offsetMap() 
    for i in range(0, len(offs)): 
        if offs[i][1] <= offset and offset[i][2] <= offset:
            return i - 1
    appendMeasuresUpToOffset(offset, part)
    return part.offsetMap()[-1][0]

def startOfMeasureContainingOffset(offset, part): 
    """ Returns the offset in quarterLengths of the beginning of
        the measure in the part containing the given offset. """
    offs = part.offsetMap() 
    for off in offs: 
        if off[1] <= offset and offset <= off[2]:
            return off[1]
        
def measureAtOffset(offset, part): 
    """ Returns the measure object inside a given part that
        contains the given offset. """
    off = part.offsetMap() 
    for off in offs: 
        if off[1] <= offset and offset <= off[2]:
            return off[0]

def barDurationAtOffset(offset, part): 
    """ Returns the bar duration at a given offset inside a part.
        Useful for determining re-adjustments of time signatures
        and ties over barlines. """
    return measureAtOffset(offset, part).barDuration
