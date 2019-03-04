# encoding: utf-8
from antlr4 import *
from PiCalcListener import PiCalcListener
from PiCalcParser import PiCalcParser
from PiCalcLexer import PiCalcLexer
import operator
import copy
import string

class SPERunner(PiCalcListener):

	def __init__(self, sesExecute, linExecute):
		## THESE VARIABLES ARE USED TO DECIDE WHAT OPERATIONS TO PERFORM
		self.doSesExecute = sesExecute
		self.doLinExecute = linExecute
		## executionStrBuilder is used to display that the execution was successful and what actions were performed (and their reduction rules)
		## errorStrBuilder is used to display any errors that occur while executing, i.e. why execution has failed
		self.executionStrBuilder = "<span class='success'>Execution successful.</span> Actions performed: \n"
		self.errorStrBuilder = ""
		## chanCounterparts is a dictionary used to store, for each channel, the name of the channel it communicates with
		##   i.e. for session endpoints, a b, chanCounterparts[a] = b and chanCounterparts[b] = a
		##   for (linear) channels, x, chanCounterparts[x] = x
		self.chanCounterparts = {}
		## parProcs is a list used to store all of the processes composed in parallel with each other at the current point of execution
		self.parProcs = []
		## variableValues is a dict used to store any values which have been assigned to a variable
		self.variableValues = {}
		## replacements is a list of dictionaries to keep track of the variables that replace bound variables as a result of reduction, in each of the composed processes
		self.replacements = []
		## delayedProcess stores the ANTLR contexts for named processes, so they can be handled later
		self.delayedProcesses = {}

	## Define custom errors, so that execution can be interrupted when an error in the user input is found.
	class executionException(Exception):
		pass

	## Walk the supplied parse tree to perform the operations requested by the webapp
	## Also performs error handling so webapp responds when exception occurs
	def doExecution(self, parseTree):
		try:
			walker = ParseTreeWalker()
			walker.walk(self, parseTree)
		except (self.executionException):
			pass

	# Given an ANTLR context of a variable, get the variable that has replaced it due to reduction, if it has been replaced
	def getReplacement(self, proc, var):
		return self.replacements[proc].get(var.getText(), var)

	# Given an evaluation of an expression, parse the value and return its ANTLR context
	def parseEvaluation(self, evaluated):
		inStrm = InputStream(str(evaluated))
		lex = PiCalcLexer(inStrm)
		tknStrm = CommonTokenStream(lex)
		par = PiCalcParser(tknStrm)
		return par.value()

	# Given an ANTLR context of an expression, evaluate the expression, and return it as a context
	def evaluateExpression(self, expr, proc):
		if isinstance(expr, PiCalcParser.StringValueContext):
			return expr.getText()
		elif isinstance(expr, PiCalcParser.BooleanValueContext):
			return expr.getText() == "True"
		elif isinstance(expr, PiCalcParser.IntegerValueContext):
			return int(expr.getText())
		elif isinstance(expr, PiCalcParser.NamedValueContext):
			return self.evaluateExpression(self.variableValues[expr.getText()], proc)
		elif isinstance(expr, PiCalcParser.ExprValueContext):
			return self.evaluateExpression(self.evaluateExpression(expr.expression(), proc), proc)
		elif isinstance(expr, PiCalcParser.EqlContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 == op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.InEqlContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 != op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntAddContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 + op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntSubContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 - op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntMultContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 * op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntDivContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			if op2 == 0:
				self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. " + self.printExpression(expr, proc) + " contains division by zero.</span>\n"
				raise self.executionException
			else:
				evaluated = op1 / op2
				return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntModContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			if op2 == 0:
				self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. " + self.printExpression(expr, proc) + " results in division by zero due to modulo.</span>\n"
				raise self.executionException
			else:
				evaluated = op1 % op2
				return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntGTContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 > op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntGTEqContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 >= op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntLTContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 < op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.IntLTEqContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 <= op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.StrConcatContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1[:-1] + op2[1:]
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.BoolNotContext):
			op = self.evaluateExpression(self.getReplacement(proc, expr.value()), proc)
			evaluated = not op
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.BoolAndContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 and op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.BoolOrContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = op1 or op2
			return self.parseEvaluation(evaluated)
		elif isinstance(expr, PiCalcParser.BoolXorContext):
			op1 = self.evaluateExpression(self.getReplacement(proc, expr.value(0)), proc)
			op2 = self.evaluateExpression(self.getReplacement(proc, expr.value(1)), proc)
			evaluated = operator.xor(op1, op2)
			return self.parseEvaluation(evaluated)

	# Given an ANTLR context for an expression, generate a string of that expression, with variable names replaced as they should be
	def printExpression(self, expr, proc):
		if isinstance(expr, PiCalcParser.StringValueContext) or isinstance(expr, PiCalcParser.BooleanValueContext) or isinstance(expr, PiCalcParser.IntegerValueContext):
			return expr.getText()
		elif isinstance(expr, PiCalcParser.NamedValueContext):
			return self.getReplacement(proc, expr).getText()
		elif isinstance(expr, PiCalcParser.ExprValueContext):
			return self.printExpression(expr.expression(), proc)
		elif isinstance(expr, PiCalcParser.EqlContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "==" + op2 + ")"
		elif isinstance(expr, PiCalcParser.InEqlContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "!=" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntAddContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "+" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntSubContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "-" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntMultContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "*" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntDivContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			if op2 == 0:
				self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. " + self.printExpression(expr, proc) + " contains division by zero.</span>\n"
				raise self.executionException
			else:
				return "(" + op1 + "/" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntModContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			if op2 == 0:
				self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. " + self.printExpression(expr, proc) + " results in division by zero due to modulo.</span>\n"
				raise self.executionException
			else:
				return "(" + op1 + "%" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntGTContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + ">" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntGTEqContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + ">=" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntLTContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "<" + op2 + ")"
		elif isinstance(expr, PiCalcParser.IntLTEqContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "<=" + op2 + ")"
		elif isinstance(expr, PiCalcParser.StrConcatContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + "++" + op2 + ")"
		elif isinstance(expr, PiCalcParser.BoolNotContext):
			op = self.printExpression(expr.value(), proc)
			return "(NOT " + op + ")"
		elif isinstance(expr, PiCalcParser.BoolAndContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + " AND " + op2 + ")"
		elif isinstance(expr, PiCalcParser.BoolOrContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + " OR " + op2 + ")"
		elif isinstance(expr, PiCalcParser.BoolXorContext):
			op1 = self.printExpression(expr.value(0), proc)
			op2 = self.printExpression(expr.value(1), proc)
			return "(" + op1 + " XOR " + op2 + ")"



	def getExecutionResults(self):
		if self.errorStrBuilder != "":
			self.executionStrBuilder = ""
		return (self.executionStrBuilder, self.errorStrBuilder)


	
	# Store named processes for later
	def enterProcessNamingNmd(self, ctx):
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()

	# Store named processes for later
	def enterProcessNamingSes(self, ctx):
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()

	# Store named processes for later
	def enterProcessNamingLin(self, ctx):
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()

	# Store value assigned to variable
	def enterVariableAssignment(self, ctx):
		self.variableValues[ctx.var.text] = ctx.value()
	
	# Store value assigned to variable
	def enterNmdTypeDeclAndAssign(self, ctx):
		self.variableValues[ctx.var.text] = ctx.value()
	
	# Store value assigned to variable
	def enterSesTypeDeclAndAssign(self, ctx):
		self.variableValues[ctx.var.text] = ctx.value()
	
	# Store value assigned to variable
	def enterLinTypeDeclAndAssign(self, ctx):
		self.variableValues[ctx.var.text] = ctx.value()



	# Store channel in chanCounterparts
	def enterChannelRestrictionNmd(self, ctx):
		self.chanCounterparts[ctx.value().getText()] = ctx.value().getText()

	# Store endpoints in chanCounterparts
	def enterSessionRestriction(self, ctx):
		self.chanCounterparts[ctx.endpoint[0].getText()] = ctx.endpoint[1].getText()
		self.chanCounterparts[ctx.endpoint[1].getText()] = ctx.endpoint[0].getText()

	# Store channel in chanCounterparts
	def enterChannelRestrictionSes(self, ctx):
		if self.doSesExecute:
			self.chanCounterparts[ctx.value().getText()] = ctx.value().getText()
		if self.doLinExecute:
			## In theory, not necessary, as same error should be caught by typechecker
			self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. Channel restrictions containing session types are not supported in linear-typed pi calculus.</span>\n"
			raise self.executionException


	# Store channel in chanCounterparts
	def enterChannelRestrictionLin(self, ctx):
		if self.doSesExecute:
			## In theory, not necessary, as same error should be caught by typechecker
			self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed. Channel restrictions containing linear types are not supported in session-typed pi calculus.</span>\n"
			raise self.executionException
		if self.doLinExecute:
			self.chanCounterparts[ctx.value().getText()] = ctx.value().getText()


	def enterComposition(self, ctx):
		if self.doSesExecute:
			self.parProcs.append(copy.deepcopy(ctx.processPrim(0)))
			self.replacements.append({})
			self.parProcs.append(copy.deepcopy(ctx.processPrim(1)))
			self.replacements.append({})
			allInact = False
			while not allInact:
				for i in range(len(self.parProcs)):
					while (
						isinstance(self.parProcs[i], PiCalcParser.SecondaryProcContext) or isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionNmdContext) or
						isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionLinContext) or isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionSesContext) or
						isinstance(self.parProcs[i], PiCalcParser.NamedProcessContext) or isinstance(self.parProcs[i], PiCalcParser.CompositionContext)
					):
						if isinstance(self.parProcs[i], PiCalcParser.SecondaryProcContext):
							self.parProcs[i] = self.parProcs[i].processSec()
						## If composed proc is restriction, add channel to chanCounterparts and use continuation
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionNmdContext):
							self.enterChannelRestrictionNmd(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionLinContext):
							self.enterChannelRestrictionLin(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionSesContext):
							self.enterChannelRestrictionSes(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						## If composed proc is named process, get full proc from delayedProcesses and replace dummy variable with real variable
						if isinstance(self.parProcs[i], PiCalcParser.NamedProcessContext):
							delayChan, delayProc = self.delayedProcesses[self.parProcs[i].name.text]
							self.replacements[i][delayChan.getText()] = self.getReplacement(i, self.parProcs[i].value())
							# if delayChan.getText() in self.chanCounterparts:
							# 	self.chanCounterparts[self.parProcs[i].value().getText()] = self.chanCounterparts[delayChan.getText()]
							# 	self.chanCounterparts[self.chanCounterparts[self.parProcs[i].value()]] = self.getReplacement(i, self.parProcs[i].value()).getText()
							self.parProcs[i] = delayProc
						## If composed proc is composition, recurse
						if isinstance(self.parProcs[i], PiCalcParser.CompositionContext):
							nestedComp = self.parProcs[i]
							del self.parProcs[i]
							self.enterComposition(nestedComp)
				reductionMade = False
				## Check for pairs that can be reduced
				for i in range(len(self.parProcs)):
					for j in range(i+1, len(self.parProcs)):
						if isinstance(self.parProcs[i], PiCalcParser.OutputContext) and isinstance(self.parProcs[j], PiCalcParser.InputSesContext):
							if (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]) and (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]):
								payloadText = self.getReplacement(i, self.parProcs[i].payloads[0]).getText()
								if isinstance(self.parProcs[i].payloads[0], PiCalcParser.ExprValueContext):
									evalExpr = self.evaluateExpression(self.parProcs[i].payloads[0].expression(), i)
									payloadText = self.printExpression(self.parProcs[i].payloads[0].expression(), i) + " = " + evalExpr.getText()
									self.replacements[j][self.parProcs[j].payload.getText()] = evalExpr
								else:
									if isinstance(self.getReplacement(i, self.parProcs[i].payloads[0]), PiCalcParser.NamedValueContext) and self.getReplacement(i, self.parProcs[i].payloads[0]).getText() in self.variableValues:
										payloadText = payloadText + " = "  + self.variableValues[self.getReplacement(i, self.parProcs[i].payloads[0]).getText()].getText()
									self.replacements[j][self.parProcs[j].payload.getText()] = self.getReplacement(i, self.parProcs[i].payloads[0])
								if self.getReplacement(i, self.parProcs[i].channel).getText() == self.getReplacement(j, self.parProcs[j].channel).getText():
									self.executionStrBuilder = self.executionStrBuilder + "Sending " + payloadText + " over " + self.getReplacement(i, self.parProcs[i].channel).getText() + ", replacing " + self.parProcs[j].payload.getText() + ". (R-StndCom)\n"
								else:
									self.executionStrBuilder = self.executionStrBuilder + "Sending " + payloadText + " from " + self.getReplacement(i, self.parProcs[i].channel).getText() + " to " + self.getReplacement(j, self.parProcs[j].channel).getText() + ", replacing " + self.parProcs[j].payload.getText() + ". (R-Com)\n"
								self.parProcs[i] = self.parProcs[i].processSec()
								self.parProcs[j] = self.parProcs[j].processSec()
								reductionMade = True
						## Vice-versa of above, code repeated so output message can be constructed
						elif isinstance(self.parProcs[i], PiCalcParser.InputSesContext) and isinstance(self.parProcs[j], PiCalcParser.OutputContext):
							if (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]) and (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]):
								payloadText = self.getReplacement(j, self.parProcs[j].payloads[0]).getText()
								if isinstance(self.parProcs[j].payloads[0], PiCalcParser.ExprValueContext):
									evalExpr = self.evaluateExpression(self.parProcs[j].payloads[0].expression(), j)
									payloadText = self.printExpression(self.parProcs[j].payloads[0].expression(), j) + " = " + evalExpr.getText()
									self.replacements[i][self.parProcs[i].payload.getText()] = evalExpr
								else:
									if isinstance(self.getReplacement(j, self.parProcs[j].payloads[0]), PiCalcParser.NamedValueContext) and self.getReplacement(j, self.parProcs[j].payloads[0]) in self.variableValues:
										payloadText = payloadText + " = "  + self.variableValues[self.getReplacement(j, self.parProcs[j].payloads[0]).getText()].getText()
									self.replacements[i][self.parProcs[i].payload.getText()] = self.getReplacement(j, self.parProcs[j].payloads[0])
								if self.getReplacement(i, self.parProcs[i].channel).getText() == self.getReplacement(j, self.parProcs[j].channel).getText():
									self.executionStrBuilder = self.executionStrBuilder + "Sending " + payloadText + " over " + self.getReplacement(j, self.parProcs[j].channel).getText() + ", replacing " + self.parProcs[i].payload.getText() + ". (R-StndCom)\n"
								else:
									self.executionStrBuilder = self.executionStrBuilder + "Sending " + payloadText + " from " + self.getReplacement(j, self.parProcs[j].channel).getText() + " to " + self.getReplacement(i, self.parProcs[i].channel).getText() + ", replacing " + self.parProcs[i].payload.getText() + ". (R-Com)\n"
								self.parProcs[i] = self.parProcs[i].processSec()
								self.parProcs[j] = self.parProcs[j].processSec()
								reductionMade = True
						elif isinstance(self.parProcs[i], PiCalcParser.SelectionContext) and isinstance(self.parProcs[j], PiCalcParser.BranchingContext):
							if (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]) and (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]):
								rCaseStrBuilder = "Selecting " + self.parProcs[i].selection.getText() + " on " + self.getReplacement(i, self.parProcs[i].channel).getText() + " out of {"
								for k in range(len(self.parProcs[j].opts)):
									rCaseStrBuilder = rCaseStrBuilder + self.parProcs[j].opts[k].getText()
									if self.parProcs[j].opts[k].getText() == self.parProcs[i].selection.getText():
										brchCont = k
									if k != len(self.parProcs[j].opts)-1:
										rCaseStrBuilder = rCaseStrBuilder + ", "
								rCaseStrBuilder = rCaseStrBuilder + "} from " + self.getReplacement(j, self.parProcs[j].channel).getText() + ". (R-Case)\n"
								self.executionStrBuilder = self.executionStrBuilder + rCaseStrBuilder
								self.parProcs[j] = self.parProcs[j].conts[brchCont]
								self.parProcs[i] = self.parProcs[i].processSec()
								reductionMade = True
						## Vice-versa of above, code repeated so output message can be constructed
						elif isinstance(self.parProcs[i], PiCalcParser.BranchingContext) and isinstance(self.parProcs[j], PiCalcParser.SelectionContext):
							if (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]) and (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]):
								rCaseStrBuilder = "Selecting " + self.parProcs[j].selection.getText() + " on " + self.getReplacement(j, self.parProcs[j].channel).getText() + " out of {"
								for k in range(len(self.parProcs[i].opts)):
									rCaseStrBuilder = rCaseStrBuilder + self.parProcs[i].opts[k].getText()
									if self.parProcs[i].opts[k].getText() == self.parProcs[j].selection.getText():
										brchCont = k
									if k != len(self.parProcs[i].opts)-1:
										rCaseStrBuilder = rCaseStrBuilder + ", "
								rCaseStrBuilder = rCaseStrBuilder + "} from " + self.getReplacement(i, self.parProcs[i].channel).getText() + ". (R-Case)\n"
								self.executionStrBuilder = self.executionStrBuilder + rCaseStrBuilder
								self.parProcs[i] = self.parProcs[i].conts[brchCont]
								self.parProcs[j] = self.parProcs[j].processSec()
								reductionMade = True
				# Check if all processes are inaction, i.e. should loop continue
				allInact = True
				for i in range(len(self.parProcs)):
					if not isinstance(self.parProcs[i], PiCalcParser.TerminationContext):
						allInact = False
				# If not all inact, and no reduction can be made, code does not reduce, throw error
				if not allInact and not reductionMade:
					self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed, code cannot be reduced any further.</span> Remaining processes: \n"
					for i in range(len(self.parProcs)):
						if not isinstance(self.parProcs[i], PiCalcParser.TerminationContext):
							self.errorStrBuilder = self.errorStrBuilder + self.parProcs[i].getText() + "\n"
					raise self.executionException
			self.doSesExecute = False


		if self.doLinExecute:
			self.parProcs.append(copy.deepcopy(ctx.processPrim(0)))
			self.replacements.append({})
			self.parProcs.append(copy.deepcopy(ctx.processPrim(1)))
			self.replacements.append({})
			allInact = False
			while(not allInact):
				for i in range(len(self.parProcs)):
					while (
						isinstance(self.parProcs[i], PiCalcParser.SecondaryProcContext) or isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionNmdContext) or
						isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionLinContext) or isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionSesContext) or
						isinstance(self.parProcs[i], PiCalcParser.NamedProcessContext) or isinstance(self.parProcs[i], PiCalcParser.CompositionContext)
					):
						if isinstance(self.parProcs[i], PiCalcParser.SecondaryProcContext):
							self.parProcs[i] = self.parProcs[i].processSec()
						## If composed proc is restriction, add channel to chanCounterparts and use continuation
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionNmdContext):
							self.enterChannelRestrictionNmd(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionLinContext):
							self.enterChannelRestrictionLin(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						if isinstance(self.parProcs[i], PiCalcParser.ChannelRestrictionSesContext):
							self.enterChannelRestrictionSes(self.parProcs[i])
							self.parProcs[i] = self.parProcs[i].processPrim()
						## If composed proc is named process, get full proc from delayedProcesses and replace dummy variable with real variable
						if isinstance(self.parProcs[i], PiCalcParser.NamedProcessContext):
							delayChan, delayProc = self.delayedProcesses[self.parProcs[i].name.text]
							self.replacements[i][delayChan.getText()] = self.parProcs[i].value()
							# if delayChan.getText() in self.chanCounterparts:
							# 	self.chanCounterparts[self.parProcs[i].value().getText()] = self.chanCounterparts[delayChan.getText()]
							# 	self.chanCounterparts[self.chanCounterparts[self.parProcs[i].value().getText()]] = self.getReplacement(i, self.parProcs[i].value()).getText()
							self.parProcs[i] = delayProc
						## If composed proc is composition, recurse
						if isinstance(self.parProcs[i], PiCalcParser.CompositionContext):
							nestedComp = self.parProcs[i]
							del self.parProcs[i]
							self.enterComposition(nestedComp)
				reductionMade = False
				for i in range(len(self.parProcs)):
					for j in range(i+1, len(self.parProcs)):
						if (isinstance(self.parProcs[i], PiCalcParser.OutputContext) or isinstance(self.parProcs[i], PiCalcParser.OutputVariantsContext)) and isinstance(self.parProcs[j], PiCalcParser.InputLinContext):
							if (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]) and (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]):
								rPiComStrBuilder = "Sending "
								for k in range(len(self.parProcs[i].payloads)):
									if isinstance(self.parProcs[i].payloads[k], PiCalcParser.ExprValueContext):
										evalExpr = self.evaluateExpression(self.parProcs[i].payloads[k].expression(), i)
										rPiComStrBuilder = rPiComStrBuilder + self.printExpression(self.parProcs[i].payloads[k].expression(), i) + " = " + evalExpr.getText()
										if k != len(self.parProcs[i].payloads)-1:
											rPiComStrBuilder = rPiComStrBuilder + ", "
										self.replacements[j][self.parProcs[j].payloads[k].getText()] = evalExpr
									else:
										if isinstance(self.getReplacement(i, self.parProcs[i].payloads[k]), PiCalcParser.NamedValueContext) and self.getReplacement(i, self.parProcs[i].payloads[k]).getText() in self.variableValues:
											rPiComStrBuilder = rPiComStrBuilder + self.getReplacement(i, self.parProcs[i].payloads[k]).getText() + " = "  + self.variableValues[self.getReplacement(i, self.parProcs[i].payloads[k]).getText()].getText()
										else:
											rPiComStrBuilder = rPiComStrBuilder + self.getReplacement(i, self.parProcs[i].payloads[k]).getText()
										if k != len(self.parProcs[i].payloads)-1:
											rPiComStrBuilder = rPiComStrBuilder + ", "
										self.replacements[j][self.parProcs[j].payloads[k].getText()] = self.getReplacement(i, self.parProcs[i].payloads[k])
								rPiComStrBuilder = rPiComStrBuilder + " over " + self.getReplacement(i, self.parProcs[i].channel).getText() + ", replacing "
								for k in range(len(self.parProcs[j].payloads)):
									rPiComStrBuilder = rPiComStrBuilder + self.parProcs[j].payloads[k].getText()
									if k != len(self.parProcs[j].payloads)-1:
										rPiComStrBuilder = rPiComStrBuilder + ", "
								rPiComStrBuilder = rPiComStrBuilder + u". (Rπ-Com)\n"
								self.executionStrBuilder = self.executionStrBuilder + rPiComStrBuilder
								self.parProcs[i] = self.parProcs[i].processSec()
								self.parProcs[j] = self.parProcs[j].processSec()
								reductionMade = True
						## Vice-versa of above, code repeated so output message can be constructed
						elif isinstance(self.parProcs[i], PiCalcParser.InputLinContext) and (isinstance(self.parProcs[j], PiCalcParser.OutputContext) or isinstance(self.parProcs[j], PiCalcParser.OutputVariantsContext)):
							if (self.getReplacement(j, self.parProcs[j].channel).getText() == self.chanCounterparts[self.getReplacement(i, self.parProcs[i].channel).getText()]) and (self.getReplacement(i, self.parProcs[i].channel).getText() == self.chanCounterparts[self.getReplacement(j, self.parProcs[j].channel).getText()]):
								rPiComStrBuilder = "Sending "
								for k in range(len(self.parProcs[j].payloads)):
									if isinstance(self.parProcs[j].payloads[k], PiCalcParser.ExprValueContext):
										evalExpr = self.evaluateExpression(self.parProcs[j].payloads[k].expression(), j)
										rPiComStrBuilder = rPiComStrBuilder + self.printExpression(self.parProcs[j].payloads[k].expression(), j) + " = " + evalExpr.getText()
										if k != len(self.parProcs[j].payloads)-1:
											rPiComStrBuilder = rPiComStrBuilder + ", "
										self.replacements[i][self.parProcs[i].payloads[k].getText()] = evalExpr
									else:
										if isinstance(self.getReplacement(j, self.parProcs[j].payloads[k]), PiCalcParser.NamedValueContext) and self.getReplacement(j, self.parProcs[j].payloads[k]).getText() in self.variableValues:
											rPiComStrBuilder = rPiComStrBuilder + self.getReplacement(j, self.parProcs[j].payloads[k]).getText() + " = "  + self.variableValues[self.getReplacement(j, self.parProcs[j].payloads[k]).getText()].getText()
										else:
											rPiComStrBuilder = rPiComStrBuilder + self.getReplacement(j, self.parProcs[j].payloads[k]).getText()
										if k != len(self.parProcs[j].payloads)-1:
											rPiComStrBuilder = rPiComStrBuilder + ", "
										self.replacements[i][self.parProcs[i].payloads[k].getText()] = self.getReplacement(j, self.parProcs[j].payloads[k])
								rPiComStrBuilder = rPiComStrBuilder + " over " + self.getReplacement(j, self.parProcs[j].channel).getText() + ", replacing "
								for k in range(len(self.parProcs[i].payloads)):
									rPiComStrBuilder = rPiComStrBuilder + self.parProcs[i].payloads[k].getText()
									if k != len(self.parProcs[i].payloads)-1:
										rPiComStrBuilder = rPiComStrBuilder + ", "
								rPiComStrBuilder = rPiComStrBuilder + u". (Rπ-Com)\n"
								self.executionStrBuilder = self.executionStrBuilder + rPiComStrBuilder
								self.parProcs[i] = self.parProcs[i].processSec()
								self.parProcs[j] = self.parProcs[j].processSec()
								reductionMade = True
						elif isinstance(self.parProcs[i], PiCalcParser.CaseContext):
							for k in range(len(self.parProcs[i].opts)):
								if self.getReplacement(i, self.parProcs[i].case).variantVal().ID().getText() == self.parProcs[i].opts[k].ID().getText():
									rPiCaseStrBuilder = "Selecting case " + self.getReplacement(i, self.parProcs[i].case).variantVal().ID().getText() + " out of cases "
									for l in range(len(self.parProcs[i].opts)):
										rPiCaseStrBuilder = rPiCaseStrBuilder + self.parProcs[i].opts[l].ID().getText()
										if l != len(self.parProcs[i].opts)-1:
											rPiCaseStrBuilder = rPiCaseStrBuilder + ", "
									rPiCaseStrBuilder = rPiCaseStrBuilder + ", replacing " + self.parProcs[i].opts[k].value().getText() + " with " + self.getReplacement(i, self.parProcs[i].case).variantVal().value().getText() + u". (Rπ-Case)\n"
									self.executionStrBuilder = self.executionStrBuilder + rPiCaseStrBuilder
									self.replacements[i][self.parProcs[i].opts[k].value().getText()] = self.getReplacement(i, self.parProcs[i].case).variantVal().value()
									self.parProcs[i] = self.parProcs[i].conts[k]
									reductionMade = True
									break;
						## Vice-versa of above, code repeated so output message can be constructed
						elif isinstance(self.parProcs[j], PiCalcParser.CaseContext):
							for k in range(len(self.parProcs[j].opts)):
								if self.getReplacement(j, self.parProcs[j].case).variantVal().ID().getText() == self.parProcs[j].opts[k].ID().getText():
									rPiCaseStrBuilder = "Selecting case " + self.getReplacement(j, self.parProcs[j].case).variantVal().ID().getText() + " out of cases "
									for l in range(len(self.parProcs[j].opts)):
										rPiCaseStrBuilder = rPiCaseStrBuilder + self.parProcs[j].opts[l].ID().getText()
										if l != len(self.parProcs[j].opts)-1:
											rCaseStrBuilder = rCaseStrBuilder + ", "
									rPiCaseStrBuilder = rPiCaseStrBuilder + ", replacing " + self.parProcs[j].opts[k].value().getText() + " with " + self.getReplacement(j, self.parProcs[j].case).variantVal().value().getText() + u". (Rπ-Case)\n"
									self.executionStrBuilder = self.executionStrBuilder + rPiCaseStrBuilder
									self.replacements[j][self.parProcs[j].opts[k].value().getText()] = self.getReplacement(j, self.parProcs[j].case).variantVal().value()
									self.parProcs[j] = self.parProcs[j].conts[k]
									reductionMade = True
									break;



				# Check if all processes are inaction, i.e. should loop continue
				allInact = True
				for i in range(len(self.parProcs)):
					if not isinstance(self.parProcs[i], PiCalcParser.TerminationContext):
						allInact = False
				# If not all inact, and no reduction can be made, code does not reduce, throw error
				if not allInact and not reductionMade:
					self.errorStrBuilder = self.errorStrBuilder + "<span class='error'>ERROR: Execution failed, code cannot be reduced any further.</span> Remaining processes: \n"
					for i in range(len(self.parProcs)):
						if not isinstance(self.parProcs[i], PiCalcParser.TerminationContext):
							self.errorStrBuilder = self.errorStrBuilder + self.parProcs[i].getText() + "\n"
					raise self.executionException
			self.doLinExecute = False