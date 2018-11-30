# Generated from PiCalc.g4 by ANTLR 4.7.1
# encoding: utf-8
from __future__ import print_function
from antlr4 import *
from io import StringIO
import sys

def serializedATN():
    with StringIO() as buf:
        buf.write(u"\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3")
        buf.write(u"\26d\4\2\t\2\4\3\t\3\3\2\3\2\3\2\3\2\3\2\3\2\6\2\r\n")
        buf.write(u"\2\r\2\16\2\16\3\2\3\2\3\2\3\2\3\2\3\2\3\2\6\2\30\n\2")
        buf.write(u"\r\2\16\2\31\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2")
        buf.write(u"\3\2\3\2\3\2\3\2\3\2\3\2\6\2,\n\2\r\2\16\2-\3\2\3\2\3")
        buf.write(u"\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3\2\3")
        buf.write(u"\2\3\2\3\2\3\2\6\2C\n\2\r\2\16\2D\3\2\3\2\3\2\3\2\3\2")
        buf.write(u"\3\2\3\2\3\2\3\2\3\2\3\2\3\2\5\2S\n\2\3\2\3\2\3\2\7\2")
        buf.write(u"X\n\2\f\2\16\2[\13\2\3\3\3\3\3\3\3\3\3\3\5\3b\n\3\3\3")
        buf.write(u"\2\3\2\4\2\4\2\2\2o\2R\3\2\2\2\4a\3\2\2\2\6\7\b\2\1\2")
        buf.write(u"\7S\7\3\2\2\b\t\7\4\2\2\t\f\5\4\3\2\n\13\7\5\2\2\13\r")
        buf.write(u"\5\4\3\2\f\n\3\2\2\2\r\16\3\2\2\2\16\f\3\2\2\2\16\17")
        buf.write(u"\3\2\2\2\17\20\3\2\2\2\20\21\7\6\2\2\21\22\5\2\2\n\22")
        buf.write(u"S\3\2\2\2\23\24\7\7\2\2\24\27\5\4\3\2\25\26\7\5\2\2\26")
        buf.write(u"\30\5\4\3\2\27\25\3\2\2\2\30\31\3\2\2\2\31\27\3\2\2\2")
        buf.write(u"\31\32\3\2\2\2\32\33\3\2\2\2\33\34\7\6\2\2\34\35\5\2")
        buf.write(u"\2\t\35S\3\2\2\2\36\37\7\t\2\2\37 \5\4\3\2 !\7\n\2\2")
        buf.write(u"!\"\5\2\2\7\"S\3\2\2\2#$\7\13\2\2$%\5\4\3\2%+\7\f\2\2")
        buf.write(u"&\'\5\4\3\2\'(\7\r\2\2()\5\2\2\2)*\7\5\2\2*,\3\2\2\2")
        buf.write(u"+&\3\2\2\2,-\3\2\2\2-+\3\2\2\2-.\3\2\2\2./\3\2\2\2/\60")
        buf.write(u"\5\4\3\2\60\61\7\r\2\2\61\62\5\2\2\2\62\63\7\16\2\2\63")
        buf.write(u"S\3\2\2\2\64\65\7\t\2\2\65\66\5\4\3\2\66\67\5\4\3\2\67")
        buf.write(u"8\7\n\2\289\5\2\2\59S\3\2\2\2:;\7\17\2\2;<\5\4\3\2<B")
        buf.write(u"\7\20\2\2=>\5\4\3\2>?\7\21\2\2?@\5\2\2\2@A\7\5\2\2AC")
        buf.write(u"\3\2\2\2B=\3\2\2\2CD\3\2\2\2DB\3\2\2\2DE\3\2\2\2EF\3")
        buf.write(u"\2\2\2FG\5\4\3\2GH\7\21\2\2HI\5\2\2\2IJ\7\16\2\2JS\3")
        buf.write(u"\2\2\2KL\7\22\2\2LM\5\4\3\2MN\7\5\2\2NO\5\4\3\2OP\7\6")
        buf.write(u"\2\2PQ\5\2\2\3QS\3\2\2\2R\6\3\2\2\2R\b\3\2\2\2R\23\3")
        buf.write(u"\2\2\2R\36\3\2\2\2R#\3\2\2\2R\64\3\2\2\2R:\3\2\2\2RK")
        buf.write(u"\3\2\2\2SY\3\2\2\2TU\f\b\2\2UV\7\b\2\2VX\5\2\2\tWT\3")
        buf.write(u"\2\2\2X[\3\2\2\2YW\3\2\2\2YZ\3\2\2\2Z\3\3\2\2\2[Y\3\2")
        buf.write(u"\2\2\\b\7\23\2\2]b\7\25\2\2^_\7\25\2\2_`\7\24\2\2`b\5")
        buf.write(u"\4\3\2a\\\3\2\2\2a]\3\2\2\2a^\3\2\2\2b\5\3\2\2\2\t\16")
        buf.write(u"\31-DRYa")
        return buf.getvalue()


class PiCalcParser ( Parser ):

    grammarFileName = "PiCalc.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ u"<INVALID>", u"'0'", u"'send('", u"','", u"').'", 
                     u"'receive('", u"'|'", u"'(new '", u"')'", u"'case '", 
                     u"' of {'", u"'>'", u"'}'", u"'branch('", u"'){'", 
                     u"':'", u"'select('", u"'*'", u"'_'" ]

    symbolicNames = [ u"<INVALID>", u"<INVALID>", u"<INVALID>", u"<INVALID>", 
                      u"<INVALID>", u"<INVALID>", u"<INVALID>", u"<INVALID>", 
                      u"<INVALID>", u"<INVALID>", u"<INVALID>", u"<INVALID>", 
                      u"<INVALID>", u"<INVALID>", u"<INVALID>", u"<INVALID>", 
                      u"<INVALID>", u"<INVALID>", u"<INVALID>", u"ID", u"WS" ]

    RULE_process = 0
    RULE_value = 1

    ruleNames =  [ u"process", u"value" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    T__13=14
    T__14=15
    T__15=16
    T__16=17
    T__17=18
    ID=19
    WS=20

    def __init__(self, input, output=sys.stdout):
        super(PiCalcParser, self).__init__(input, output=output)
        self.checkVersion("4.7.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None



    class ProcessContext(ParserRuleContext):

        def __init__(self, parser, parent=None, invokingState=-1):
            super(PiCalcParser.ProcessContext, self).__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PiCalcParser.RULE_process

     
        def copyFrom(self, ctx):
            super(PiCalcParser.ProcessContext, self).copyFrom(ctx)


    class BranchingContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.BranchingContext, self).__init__(parser)
            self.channel = None # ValueContext
            self._value = None # ValueContext
            self.option = list() # of ValueContexts
            self._process = None # ProcessContext
            self.cont = list() # of ProcessContexts
            self.copyFrom(ctx)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)

        def process(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ProcessContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ProcessContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterBranching"):
                listener.enterBranching(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitBranching"):
                listener.exitBranching(self)


    class InputContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.InputContext, self).__init__(parser)
            self.channel = None # ValueContext
            self._value = None # ValueContext
            self.payload = list() # of ValueContexts
            self.copyFrom(ctx)

        def process(self):
            return self.getTypedRuleContext(PiCalcParser.ProcessContext,0)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterInput"):
                listener.enterInput(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitInput"):
                listener.exitInput(self)


    class CompositionContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.CompositionContext, self).__init__(parser)
            self.copyFrom(ctx)

        def process(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ProcessContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ProcessContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterComposition"):
                listener.enterComposition(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitComposition"):
                listener.exitComposition(self)


    class ChannelRestrictionContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.ChannelRestrictionContext, self).__init__(parser)
            self.copyFrom(ctx)

        def value(self):
            return self.getTypedRuleContext(PiCalcParser.ValueContext,0)

        def process(self):
            return self.getTypedRuleContext(PiCalcParser.ProcessContext,0)


        def enterRule(self, listener):
            if hasattr(listener, "enterChannelRestriction"):
                listener.enterChannelRestriction(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitChannelRestriction"):
                listener.exitChannelRestriction(self)


    class SessionRestrictionContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.SessionRestrictionContext, self).__init__(parser)
            self._value = None # ValueContext
            self.endpoint = list() # of ValueContexts
            self.copyFrom(ctx)

        def process(self):
            return self.getTypedRuleContext(PiCalcParser.ProcessContext,0)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterSessionRestriction"):
                listener.enterSessionRestriction(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitSessionRestriction"):
                listener.exitSessionRestriction(self)


    class SelectionContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.SelectionContext, self).__init__(parser)
            self.channel = None # ValueContext
            self.selection = None # ValueContext
            self.copyFrom(ctx)

        def process(self):
            return self.getTypedRuleContext(PiCalcParser.ProcessContext,0)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterSelection"):
                listener.enterSelection(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitSelection"):
                listener.exitSelection(self)


    class OutputContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.OutputContext, self).__init__(parser)
            self.channel = None # ValueContext
            self._value = None # ValueContext
            self.payload = list() # of ValueContexts
            self.copyFrom(ctx)

        def process(self):
            return self.getTypedRuleContext(PiCalcParser.ProcessContext,0)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterOutput"):
                listener.enterOutput(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitOutput"):
                listener.exitOutput(self)


    class TerminationContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.TerminationContext, self).__init__(parser)
            self.copyFrom(ctx)


        def enterRule(self, listener):
            if hasattr(listener, "enterTermination"):
                listener.enterTermination(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitTermination"):
                listener.exitTermination(self)


    class CaseContext(ProcessContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ProcessContext)
            super(PiCalcParser.CaseContext, self).__init__(parser)
            self.case = None # ValueContext
            self._value = None # ValueContext
            self.option = list() # of ValueContexts
            self._process = None # ProcessContext
            self.cont = list() # of ProcessContexts
            self.copyFrom(ctx)

        def value(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ValueContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ValueContext,i)

        def process(self, i=None):
            if i is None:
                return self.getTypedRuleContexts(PiCalcParser.ProcessContext)
            else:
                return self.getTypedRuleContext(PiCalcParser.ProcessContext,i)


        def enterRule(self, listener):
            if hasattr(listener, "enterCase"):
                listener.enterCase(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitCase"):
                listener.exitCase(self)



    def process(self, _p=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = PiCalcParser.ProcessContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 0
        self.enterRecursionRule(localctx, 0, self.RULE_process, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,4,self._ctx)
            if la_ == 1:
                localctx = PiCalcParser.TerminationContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 5
                self.match(PiCalcParser.T__0)
                pass

            elif la_ == 2:
                localctx = PiCalcParser.OutputContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 6
                self.match(PiCalcParser.T__1)
                self.state = 7
                localctx.channel = self.value()
                self.state = 10 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 8
                    self.match(PiCalcParser.T__2)
                    self.state = 9
                    localctx._value = self.value()
                    localctx.payload.append(localctx._value)
                    self.state = 12 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==PiCalcParser.T__2):
                        break

                self.state = 14
                self.match(PiCalcParser.T__3)
                self.state = 15
                self.process(8)
                pass

            elif la_ == 3:
                localctx = PiCalcParser.InputContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 17
                self.match(PiCalcParser.T__4)
                self.state = 18
                localctx.channel = self.value()
                self.state = 21 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 19
                    self.match(PiCalcParser.T__2)
                    self.state = 20
                    localctx._value = self.value()
                    localctx.payload.append(localctx._value)
                    self.state = 23 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==PiCalcParser.T__2):
                        break

                self.state = 25
                self.match(PiCalcParser.T__3)
                self.state = 26
                self.process(7)
                pass

            elif la_ == 4:
                localctx = PiCalcParser.ChannelRestrictionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 28
                self.match(PiCalcParser.T__6)
                self.state = 29
                self.value()
                self.state = 30
                self.match(PiCalcParser.T__7)
                self.state = 31
                self.process(5)
                pass

            elif la_ == 5:
                localctx = PiCalcParser.CaseContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 33
                self.match(PiCalcParser.T__8)
                self.state = 34
                localctx.case = self.value()
                self.state = 35
                self.match(PiCalcParser.T__9)
                self.state = 41 
                self._errHandler.sync(self)
                _alt = 1
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt == 1:
                        self.state = 36
                        localctx._value = self.value()
                        localctx.option.append(localctx._value)
                        self.state = 37
                        self.match(PiCalcParser.T__10)
                        self.state = 38
                        localctx._process = self.process(0)
                        localctx.cont.append(localctx._process)
                        self.state = 39
                        self.match(PiCalcParser.T__2)

                    else:
                        raise NoViableAltException(self)
                    self.state = 43 
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

                self.state = 45
                localctx._value = self.value()
                localctx.option.append(localctx._value)
                self.state = 46
                self.match(PiCalcParser.T__10)
                self.state = 47
                localctx._process = self.process(0)
                localctx.cont.append(localctx._process)
                self.state = 48
                self.match(PiCalcParser.T__11)
                pass

            elif la_ == 6:
                localctx = PiCalcParser.SessionRestrictionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 50
                self.match(PiCalcParser.T__6)
                self.state = 51
                localctx._value = self.value()
                localctx.endpoint.append(localctx._value)
                self.state = 52
                localctx._value = self.value()
                localctx.endpoint.append(localctx._value)
                self.state = 53
                self.match(PiCalcParser.T__7)
                self.state = 54
                self.process(3)
                pass

            elif la_ == 7:
                localctx = PiCalcParser.BranchingContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 56
                self.match(PiCalcParser.T__12)
                self.state = 57
                localctx.channel = self.value()
                self.state = 58
                self.match(PiCalcParser.T__13)
                self.state = 64 
                self._errHandler.sync(self)
                _alt = 1
                while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                    if _alt == 1:
                        self.state = 59
                        localctx._value = self.value()
                        localctx.option.append(localctx._value)
                        self.state = 60
                        self.match(PiCalcParser.T__14)
                        self.state = 61
                        localctx._process = self.process(0)
                        localctx.cont.append(localctx._process)
                        self.state = 62
                        self.match(PiCalcParser.T__2)

                    else:
                        raise NoViableAltException(self)
                    self.state = 66 
                    self._errHandler.sync(self)
                    _alt = self._interp.adaptivePredict(self._input,3,self._ctx)

                self.state = 68
                localctx._value = self.value()
                localctx.option.append(localctx._value)
                self.state = 69
                self.match(PiCalcParser.T__14)
                self.state = 70
                localctx._process = self.process(0)
                localctx.cont.append(localctx._process)
                self.state = 71
                self.match(PiCalcParser.T__11)
                pass

            elif la_ == 8:
                localctx = PiCalcParser.SelectionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 73
                self.match(PiCalcParser.T__15)
                self.state = 74
                localctx.channel = self.value()
                self.state = 75
                self.match(PiCalcParser.T__2)
                self.state = 76
                localctx.selection = self.value()
                self.state = 77
                self.match(PiCalcParser.T__3)
                self.state = 78
                self.process(1)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 87
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,5,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = PiCalcParser.CompositionContext(self, PiCalcParser.ProcessContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_process)
                    self.state = 82
                    if not self.precpred(self._ctx, 6):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                    self.state = 83
                    self.match(PiCalcParser.T__5)
                    self.state = 84
                    self.process(7) 
                self.state = 89
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,5,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class ValueContext(ParserRuleContext):

        def __init__(self, parser, parent=None, invokingState=-1):
            super(PiCalcParser.ValueContext, self).__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PiCalcParser.RULE_value

     
        def copyFrom(self, ctx):
            super(PiCalcParser.ValueContext, self).copyFrom(ctx)



    class UnitValueContext(ValueContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ValueContext)
            super(PiCalcParser.UnitValueContext, self).__init__(parser)
            self.copyFrom(ctx)


        def enterRule(self, listener):
            if hasattr(listener, "enterUnitValue"):
                listener.enterUnitValue(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitUnitValue"):
                listener.exitUnitValue(self)


    class VariantValueContext(ValueContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ValueContext)
            super(PiCalcParser.VariantValueContext, self).__init__(parser)
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(PiCalcParser.ID, 0)
        def value(self):
            return self.getTypedRuleContext(PiCalcParser.ValueContext,0)


        def enterRule(self, listener):
            if hasattr(listener, "enterVariantValue"):
                listener.enterVariantValue(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitVariantValue"):
                listener.exitVariantValue(self)


    class NameContext(ValueContext):

        def __init__(self, parser, ctx): # actually a PiCalcParser.ValueContext)
            super(PiCalcParser.NameContext, self).__init__(parser)
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(PiCalcParser.ID, 0)

        def enterRule(self, listener):
            if hasattr(listener, "enterName"):
                listener.enterName(self)

        def exitRule(self, listener):
            if hasattr(listener, "exitName"):
                listener.exitName(self)



    def value(self):

        localctx = PiCalcParser.ValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_value)
        try:
            self.state = 95
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,6,self._ctx)
            if la_ == 1:
                localctx = PiCalcParser.UnitValueContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 90
                self.match(PiCalcParser.T__16)
                pass

            elif la_ == 2:
                localctx = PiCalcParser.NameContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 91
                self.match(PiCalcParser.ID)
                pass

            elif la_ == 3:
                localctx = PiCalcParser.VariantValueContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 92
                self.match(PiCalcParser.ID)
                self.state = 93
                self.match(PiCalcParser.T__17)
                self.state = 94
                self.value()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx, ruleIndex, predIndex):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[0] = self.process_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def process_sempred(self, localctx, predIndex):
            if predIndex == 0:
                return self.precpred(self._ctx, 6)
         




