#!/usr/local/bin/python
#

"""
Copyright 2006 Jeff Younker 

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
       conditions and the following disclaimer.
   2. Redistributions in binary form must reproduce the above copyright notice, this
       list of conditions and the following disclaimer in the document ation and/or
      other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY JEFF YOUNKER ``AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITE
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
THE FREEBSD PROJECT OR CONTRIBUTORS BE LIABLE FOR ANY
DIR ECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.
"""


import inspect
from sets import Set
import sys
import traceback
from unittest import TestCase

from decorator import decorator


class RecordedCallsWereNotReplayedCorrectly(Exception):
    pass


class PlaybackFailure(Exception):
    pass


class RecordingError(Exception):
    pass


class IllegalPlaybackRecorded(RecordingError):
    pass



@decorator
def usePymock(func, *args, **vargs):
    PyMockTestCase.sharedController = Controller()
    try:
        return func(*args, **vargs)
    finally:
        PyMockTestCase.sharedController.restore()
        PyMockTestCase.sharedController = None


@decorator
def originateException(f, *pargs, **vargs):
    try:
        return f(*pargs, **vargs)
    except:
        raise sys.exc_info()[1]


def all(seq):
    for x in seq:
        if not x:
            return False
    return True


class PyMockTestCase(TestCase):

    # class variable used by jmock style calls
    sharedController = None
    # so that nosetests run
    context = None
    
    def setUp(self):
        self.controller = Controller()
        PyMockTestCase.sharedController = self.controller
        
    def tearDown(self):
        """Clean out configured pymock contollers.
        
        We clean up after each test run to ensure that the "pymock not initialized" check
        works correctly.
        """
        PyMockTestCase.sharedController.restore()        
        PyMockTestCase.sharedController = None
        self.controller = None

    def __getattr__(self, name):
        return getattr(self.controller, name)


class InterfaceMixin(object):

    def mock(self, klass=object):
        return MockObject(self, klass)
   
    def generator(self, functionCall=None, yieldValues=[], terminalException=None):
        """Turn the last function call into a generator"""
        functionCall = self.actionUnderConstruction
        generatorCall = GeneratorAction.fromAction(functionCall)
        self.actions.pop(functionCall)
        self.record(generatorCall)
        for x in yieldValues:
            self.setReturn(x)
        if terminalException != None:
            self.setException(terminalException)
        
    def expects(self, *pargs, **vargs):
        if self.actionUnderConstruction is None:
            self.activeMock(*pargs, **vargs)
        else:
            self.actionUnderConstruction.value(*pargs, **vargs)
        return self
    
    def returns(self, value):
        self.setReturn(value)
        return self

    def raises(self, exc):
        self.setException(exc)
        return self
    
    def setReturn(self, value):
        self.actionUnderConstruction.value = value

    def expectAndReturn(self, expr, value):
        self.setReturn(value)
                
    def setException(self, exc):
        self.actionUnderConstruction.throws = exc

    def expectAndRaise(self, expr, exc):
        self.setException(exc)
    
    def setCount(self, exactly=1):
        self.actionUnderConstruction.playbackPolicy = FixedCountPolicy(exactly)
        return self
    
    set_count = setCount

    def once(self):
        return self.setCount(1)
    
    def twice(self):
        return self.setCount(2)
    
    def atLeast(self, limit=1):
        self.actionUnderConstruction.playbackPolicy = MinimumPlaybackPolicy(limit)
        return self
    
    at_least = atLeast
    
    def zeroOrMore(self):
        return self.atLeast(0)
    
    zero_or_more = zeroOrMore

    def oneOrMore(self):
        return self.atLeast(1)

    one_or_more = oneOrMore

    def generates(self, *pargs, **vargs):
        self.generator(yieldValues=pargs, terminalException=vargs.get('ending', None))
        return self

    def getField(self, obj, field):
        accessPath = (repr(obj), 'propertyOp(%s)' % field)
        returnObject = MockObject(self, obj, (repr(self), accessPath + (':',)))
        getAttribute = GetAttributeAction(field, accessPath, returnObject)
        return self.recordOrPlayback(getAttribute)

    def setField(self, obj, field, value):
        accessPath = (repr(obj), 'propertyOp(%s)' % field)
        setAttribute = SetAttributeAction(None, field, accessPath, value)
        return self.recordOrPlayback(setAttribute)


class OverrideMixin(object):
    
    def __init__(self):
        self.preservedValues = []
    
    def override(self, obj, field, value=None):
        """Overrides an attribute or a property"""
        # TODO:  How should these be integrated?
        self.assertCanBeMonkeyPatched(obj)
        if value is not None:
            self.overrideAttributeWithSuppliedValue(obj, field, value)
#        elif getattr(obj, field) is None:
#            self.overrideAttribute(obj, field)
        elif self.isProperty(obj, field):
            self.overrideProperty(obj, field)
        else:
            self.overrideAttribute(obj, field)
        return self
        
    def overrideAttributeWithSuppliedValue(self, obj, field, value):
        """Override with something other than a mock"""
        existingAttribute = getattr(obj, field)
        if isinstance(existingAttribute, MockObject):
            raise IllegalPlaybackRecorded("Tried to override a mock with a specific value")           
        self.overrideExistingAttribute(obj, field, value, existingAttribute)
        self.actionUnderConstruction = OverrideActionForTrackingValues(value)
        
    def overrideAttribute(self, obj, field):
        """Overrides an attribute"""
        # TODO:  COMPARE THIS METHOD ASAP (was override)... WTF is VALUE= FOR?
        #    old method signature is: overrideAttribute(self, obj, field, value=None):
        existingAttribute = getattr(obj, field)
        mockToManipulate = self.mockToManipulate(existingAttribute)
        if not isinstance(existingAttribute, MockObject):           
            self.overrideExistingAttribute(obj, field, mockToManipulate, existingAttribute)
        self.actionUnderConstruction = OverrideActionForTrackingValues(mockToManipulate)
        
    def overrideExistingAttribute(self, obj, field, value, existingAttribute):
        self.preservedValues.append(FunctionOverride(obj, field, existingAttribute))
        setattr(obj, field, value)
        return value
    
    def mockToManipulate(self, existingAttribute):
        if isinstance(existingAttribute, MockObject):
            return existingAttribute
        else:
            return self.mock()            

    def isProperty(self, obj, field):
        """Returns True if obj.field is a property and False otherwise"""
        if obj.__dict__.has_key(field):
            return False
        for klass in inspect.getmro(obj.__class__):
            if klass.__dict__.has_key(field) and isinstance(klass.__dict__[field], property):
                return True
        return False
    
    def overrideProperty(self, obj, field):
        """Overrides a property by altering obj.__class__"""
        prop = property(lambda x: self.getField(x, field),
                     lambda x, value: self.setField(x, field, value),
                     lambda x: self.getField(x, field))
        if not self.isAttachedToProxyClass(obj):
            self.preservedValues.append(ClassOverride(obj, obj.__class__))
            self.attachObjectToProxyClass(obj)
        self.setOverriddenProperty(obj, field, prop)
        return self
        
    proxyClassNamePrefix = '__Proxied__'
    
    def isAttachedToProxyClass(self, obj):
        return obj.__class__.__name__.startswith(self.proxyClassNamePrefix)

    def attachObjectToProxyClass(self, obj):
        proxyClass = self.proxyClassForObject(obj)
        obj.__class__ = proxyClass

    def proxyClassForObject(self, obj):
        return type(self.proxyClassNamePrefix + obj.__class__.__name__, (), dict(obj.__class__.__dict__))

    def setOverriddenProperty(self, obj, attr, prop):
        setattr(obj.__class__, attr, prop)

    def assertCanBeMonkeyPatched(self, obj):
        """Raises an exception if the object can't be monkey patched"""
        try:
            getattr(obj, '__dict__')
            return True
        except AttributeError:
            raise RecordingError("This object can't be modified.  Try replacing it with a mock.")
            


class RecordPlaybackEngineMixin(object):
    
    RECORD = 1
    PLAYBACK = 2
    
    isPlayingBack = property(lambda self: self.mode == self.PLAYBACK)
    isRecording = property(lambda self: self.mode == self.RECORD)
    
    def __init__(self):
        self.mode = self.RECORD
        self.actions = ActionCache()
        self.actionUnderConstruction = None
        self.activeMock = None

    def getActiveMock(self):
        return self.actionUnderConstruction.mock
        
    def restore(self):
        self.preservedValues.reverse()
        for override in self.preservedValues:
            override.restore()    
    
    def reset(self):
        self.actions.clear()
        self.actionUnderConstruction = None
        self.activeMock = None
        self.mode = self.RECORD
    
    def replay(self):
        self.mode = self.PLAYBACK
    
    def verify(self):
        for x in self.actions:
            if not x.hasBeenPlayedBack:
                raise RecordedCallsWereNotReplayedCorrectly()

    def recordOrPlayback(self, action):
        if self.isPlayingBack:
            return self.playback(action)
        else:
            return self.record(action)
    
    def playback(self, action):
        recordedAction = self.actions.get(action)
        if recordedAction == None:
            raise PlaybackFailure("No further actions defined")
        elif not action == recordedAction:
            raise PlaybackFailure("Inappropriate action")
        else:
            return self.playBackActionAndRemoveIfNeeded(recordedAction)

    def playBackActionAndRemoveIfNeeded(self, action):
        """Plays back an action, returns the results,  and removes the action if needed"""
        try:
            return action.playback()
        finally:
            if action.isReadyForRemoval:
                self.actions.pop(action)
                            
    def record(self, action):
        if self.actions.contains(action) and self.actions.get(action).playbackPolicy.hasUnlimitedPlaybacks:
            raise IllegalPlaybackRecorded("You cannot record additional playbacks when you have defined an unlimited playback")
        else:
            self.actions.append(action)
            self.actionUnderConstruction = action
            return action.record()


class Controller(RecordPlaybackEngineMixin, InterfaceMixin, OverrideMixin):
    
    def __init__(self):
        RecordPlaybackEngineMixin.__init__(self)
        OverrideMixin.__init__(self)


class FunctionOverride(object):
    
    def __init__(self, obj, fieldName, originalValue):
        self.obj = obj
        self.fieldName = fieldName
        self.originalValue = originalValue
    
    def restore(self):
        #self.obj.__dict__[self.fieldName] = self.originalValue
        setattr(self.obj, self.fieldName, self.originalValue)


class ClassOverride(object):
    
    def __init__(self, obj, originalClass):
        self.obj = obj
        self.originalClass = originalClass
    
    def restore(self):
        self.obj.__class__ = self.originalClass


class PropertyOverride(object):
    
    def __init__(self, obj, attr, property):
        self.obj = obj
        self.attr = attr
        self.oldProperty = property
        
    def restore(self):
        if self.oldProperty is None:
            del self.obj.__class__.__dict__[self.attr]
        else:
            self.obj.__class__.__dict__[self.attr] = self.oldProperty


class MockObject(object):
    
    def __init__(self, controller, klass, accessPath=None):
        self.__backingMock = MockObjectBacking(self, controller, klass, accessPath)

    @originateException
    def __setattr__(self, name, value):
        if name == '_MockObject__backingMock':
            self.__dict__[name] = value
            return
        else:
            setAttrAction = SetAttributeAction(self, name, self.__backingMock.accessPath, value)            
            self.__backingMock.controller.recordOrPlayback(setAttrAction)

    @originateException
    def __getattr__(self, name):
        if name == '__MockObject__backingMock':
            return self.__dict__[name]
        returnObject = MockObject(self.__backingMock.controller, object, self.__backingMock.accessPath + (name,))
        getAttribute = GetAttributeAction(name, self.__backingMock.accessPath, returnObject)
        return self.__backingMock.controller.recordOrPlayback(getAttribute)

#    @originateException
    def __iter__(self):
        return self.__backingMock.iter()
 
    @originateException
    def __call__(self, *pargs, **vargs):
        return self.__backingMock.call(*pargs, **vargs)

    @originateException
    def __len__(self):
        return self.__backingMock.prefixCall('len', self)
    
    @originateException
    def __iadd__(self, x):
        return self.__backingMock.mockfunc('__iadd__(x)', (self, x))

    @originateException
    def __isub__(self, x):
        return self.__backingMock.mockfunc('__isub__(x)', (self, x))

    @originateException
    def __getitem__(self, index):
        return self.__backingMock.mockfunc('__getitem__(x)', (self, index))

    @originateException
    def __setitem__(self, index, value):
        return self.__backingMock.mockfunc('__setitem__(x, y)', (self, index, value))

    @originateException
    def __delitem__(self, index):
        return self.__backingMock.mockfunc('__delitem__(x)', (self, index))
    
    @originateException
    def __contains__(self, value):
        return self.__backingMock.mockfunc('x in y', (self, value))

    @originateException
    def __bool__(self):
        return self.__backingMock.mockfunc('__bool__()', (self,))


class Expression(object):
    """Represents the entire expression sequence under construction"""

    def expectedActionsList(self):
        """List of actions"""
        pass
    
    def setPolicy(self, policy):
        """Set policy for every action in the expression"""
        pass    
    

class MockObjectBacking(object):

    def __init__(self, mockObject, controller, klass, accessPath=None):
        self.controller = controller
        self.accessPath = self.initializeAccessPath(mockObject, accessPath)
 
    def initializeAccessPath(self, mockObject, accessPath):
        if accessPath == None:
            return (mockObject, )
        else:
            return accessPath

    def call(self, *pargs, **vargs):
        accessPath = self.accessPath + ('()',)
        returnObject = MockObject(self.controller, object, accessPath)
        functionCall = FunctionCallAction(accessPath, pargs, vargs, returnObject)
        return self.controller.recordOrPlayback(functionCall)

    def mockfunc(self, accessElt, pargs):
        accessPath = self.accessPath + (accessElt,)
        returnObject = MockObject(self.controller, object, accessPath)
        functionCall = FunctionCallAction(accessPath, pargs, {}, returnObject)
        return self.controller.recordOrPlayback(functionCall)

    def prefixCall(self, accessString, mock):
        accessPath = self.accessPath + (accessString,)
        functionCall = FunctionCallAction(accessPath, (mock, ), {}, 0)
        return self.controller.recordOrPlayback(functionCall)

    def iter(self):
        accessPath = self.accessPath + ('__iter__()', )
        generatorCall = GeneratorAction(accessPath, (), ())
        return self.controller.recordOrPlayback(generatorCall)


class MockProperty(object):
    """Used to override single properties in a non-mock object"""
    
    def __init__(self, controller, mockObject):
        self.controller = controller
        self.mockObject = mockObject


class ActionKey(object):
    """Key into action cache.  Implements constraint matching."""
    
    def __init__(self, accessPath, owner, pargs, vargs):
        self.accessPath = accessPath
        self.owner = owner
        self.pargs = pargs
        self.vargs = vargs

    def __hash__(self):
        return self.accessPath.__hash__() * self.owner.__hash__() * len(self.pargs) * len(self.vargs)

    def convertToMaster(self):
        self.pargs = self.seqWithConstraints(self.pargs)
        self.vargs = self.dictWithConstraints(self.vargs)

    def seqWithConstraints(self, seq):
        return tuple([self.constrained(x) for x in seq])
    
    def dictWithConstraints(self, d):
        for (k, v) in d.items():
            d[k] = self.constrained(v)
        return d
    
    def constrained(self, x):
        if isinstance(x, Constraint):
            return x
        else:
            return IsSame(x)

    def __eq__(self, ak):
        return (self.accessPath == ak.accessPath and
                   self.owner == ak.owner and
                   self.pargs == ak.pargs and
                   self.vargs == ak.vargs)
    

class BaseAction(object):
    
    def __init__(self, key):
        """Field description"""
        self.key = key
        self.playbackPolicy = FixedCountPolicy(1)
        self._throws = None

    throws = property(lambda self: self._throws, lambda self, v: self.__dict__.__setitem__('_throws', v))
        
    def __eq__(self, x):
        """Equality based on fields and type"""
        if None == x:
            return False
        else:
            return self.key == x.key and \
                    self.__class__ == x.__class__
        
    def __str__(self):
        return str((self.key, self.__class__))
    
    def playback(self):
        self.playbackPolicy.playback()
        if self.throws:
            raise self.throws

    def record(self):
        return self
    
    isReadyForRemoval = property(lambda self: self.playbackPolicy.isReadyForRemoval)
    hasBeenPlayedBack = property(lambda self: self.playbackPolicy.hasBeenPlayedBack)


class OverrideActionForTrackingValues(BaseAction):
    
    def __init__(self, value):
        self.value = value


class Statement(object):
    
    def setPolicy(self):
        pass
    
    def __init__(self):
        self.actions = []
        self.resulting = None
    
    def nextKey(self, partialAccessPath, pargs, vargs):
        pass
        
    def newAction(self, partialAccessPath, pargs, vargs):
        pass
    
        


class Constraint(object):            
    pass


class Any(Constraint):

    def __eq__(self, value):
        return True


class IsEq(Constraint):

    def __init__(self, value):
        self.value = value

    def __eq__(self, value):
        return self.value == value


class IsSame(Constraint):
    
    def __init__(self, value):
        self.value = value

    def __eq__(self, value):
        return self.value is value


class IfTrue(Constraint):

    def __init__(self, func):
        self.func = func

    def __eq__(self, value):
        return self.func(value)



class BaseOfExpression(BaseAction):
    
    def __init__(self, value):
        self.value = value

class SetAttributeAction(BaseAction):
    
    def __init__(self, mockObject, field, key, value):
        """Set an attribute"""
        super(SetAttributeAction, self).__init__(key + (field, ))
        self.field = field
        self.value = value
    
    
    def __eq__(self, x):
        """Equality based on both slot identity and value"""
        return super(SetAttributeAction, self).__eq__(x) and self.value == x.value


    def __str__(self):
        return "%s = %s" % (str(self.field), str(self.value))


    def record(self):
        return self
    


class GetAttributeAction(BaseAction):
    
    def __init__(self, field, key, defaultValueMockObject):
        """Get an attribute with no method specified"""
        super(GetAttributeAction, self).__init__(key + (field,))
        self.field = field
        self.value = defaultValueMockObject
    
    def playback(self):
        super(GetAttributeAction, self).playback()
        return self.value

    def record(self):
        return self.value



class CallAction(BaseAction):

    def __init__(self, key, pargs, vargs):
        super(CallAction, self).__init__(key)
        self.pargs = pargs
        self.vargs = vargs
    
    def __eq__(self, x):
        return isinstance(x, CallAction) and \
                self.key == x.key and \
                self.pargs == x.pargs and \
                self.vargs == x.vargs

    

class FunctionCallAction(CallAction):
    
    def __init__(self, key, pargs, vargs, mockObject):
        super(FunctionCallAction, self).__init__(key, pargs, vargs)
        self.value = mockObject

    def playback(self):
        super(FunctionCallAction, self).playback()
        return self.value

    def record(self):
        return self.value
    


class GeneratorAction(CallAction):
    
    def __init__(self, key, pargs, vargs):
        super(GeneratorAction, self).__init__(key, pargs, vargs)
        self.values = []


    @classmethod
    def fromAction(cls, action):
        generatorAction = GeneratorAction(action.key, action.pargs, action.vargs)
        generatorAction.playbackPolicy = action.playbackPolicy
        return generatorAction
    

    def record(self):
        return None
    
                    
    def playback(self):
        super(GeneratorAction, self).playback()
        return self.playbackGenerator()

    
    def playbackGenerator(self):
        for (value, exc) in self.values:
            if exc == None:
                yield value
            else:
                raise exc


    def assertRecordingIsNotComplete(self):
        if  len(self.values):
            (value, exc) = self.values[-1]
            if exc != None:
                raise IllegalPlaybackRecorded


    def setValue(self, x):
        self.assertRecordingIsNotComplete()
        self.values.append((x, None))


    def setException(self, exc):
        self.assertRecordingIsNotComplete()
        self.values.append((None, exc))


    value = property(lambda self: None, lambda self, x: self.setValue(x))

    throws = property(lambda self: None, lambda self, x: self.setException(x))
    


class FixedCountPolicy(object):
    
    def __init__(self, count=1):
        self.remaining = count
        
    hasBeenPlayedBack = property(lambda x: x.remaining == 0)
    isReadyForRemoval = property(lambda x: x.remaining == 0)
    hasUnlimitedPlaybacks = False;


    def playback(self):
        if self.remaining == 0:
            raise RecordedCallsWereNotReplayedCorrectly()
        else:
            self.remaining = self.remaining - 1    


class MinimumPlaybackPolicy(object):
    
    def __init__(self, count=1):
        self.remaining = count
        
    hasBeenPlayedBack = property(lambda x: x.remaining == 0)
    isReadyForRemoval = False
    hasUnlimitedPlaybacks = True;


    def playback(self):
        self.remaining = max(0, self.remaining - 1)


class ActionCache(object):

    def __init__(self):
        self.actions = {}
    
    def clear(self):
        self.actions = {}
        
    def __len__(self):
        return len(self.actions)    
    
    def contains(self, action):
        return self.actions.has_key(action.key)
        
    def append(self, action):
        if not self.contains(action):
            self.actions[action.key] = []
        self.actions[action.key].append(action)
        
    def get(self, action, default=None):
        if not self.contains(action):
            return None
        else:
            return self.actions[action.key][0]
    
    def pop(self, action):
        if not self.contains(action):
            return None
        else:
            queue = self.actions[action.key]
            if len(queue) == 1:
                del self.actions[action.key]
            else:
                self.actions[action.key] = queue[1:]
            return queue[0]
           
    def __iter__(self):
        for queue in self.actions.values():
            for x in queue:
                yield x
