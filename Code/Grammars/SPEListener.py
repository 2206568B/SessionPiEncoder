# encoding: utf-8
from antlr4 import *
from PiCalcListener import PiCalcListener
from PiCalcParser import PiCalcParser
from PiCalcLexer import PiCalcLexer
from VariableNameCollector import VariableNameCollector
import copy
import string

class SPEListener(PiCalcListener):

	def __init__(self, sesTypeCheck, linTypeCheck, encode, varNameList):
		## THESE VARIABLES ARE USED TO DECIDE WHAT OPERATIONS TO PERFORM
		self.doSesTypeChecking = sesTypeCheck
		self.doLinTypeChecking = linTypeCheck
		self.doEncoding = encode
		self.stateTest = ()
		## THESE VARIABLES ARE USED REGARDLESS OF OPERATION
		## delayedProcesses stores the ANTLR contexts for named processes so they can be handled later
		##   When a process P is named, the processing of P should not be performed until P appears in the user-input process.
		##   So the ANTLR context for the process is stored until later.
		##   The ANTLR context of the type in the type annotation is also stored.
		self.delayedProcesses = {}
		## THESE VARIABLES ARE USED FOR TYPECHECKING
		## typeCheckStrBuilder is used to display that the typechecking was succesful, and what typechecking rules were applied.
		##   ◻ is used as a placeholder for the rules, ▵ is used as a placeholder for commas.
		## tcStrIndent is used to indent the typechecking output for improved readability
		## tcErrorStrBuilder is used to display any errors that occur while typechecking, i.e. why typechecking has failed.
		## gamma is the current type context
		## gammaStack is a stack of type contexts to be used
		##   Whenever typechecking a process requires typechecking the continuation process,
		##   the gamma to be used to typecheck that process is pushed onto the stack
		##   The listener then traverses to the continuation process, and pops the required gamma off the stack
		##   Composition pushes two different gammas, branch pushes multiple copies of the same gamma
		##   gammaStack has an empty gamma by default, in case there are no type declarations given
		##   This default is discarded if declarations are present
		## exprGamma is used to save the gamma which should be used to typecheck an expression
		##   Expression typechecking functions can not access gammas from the stack, so must be saved elsewhere
		## typeNames is a dictionary containing any types which have been given names
		##   i.e. if there is a statement 'type foo := ?Int.end', typeNames['foo'] contains a context representing ?Int.end
		##   this is used when initially adding types to gamma, that is, gamma uses the full type, not the name
		## replacedVars is used to keep track of which variables are replaced due to named processes
		##   i.e. if there is a process name declaration proc(a : T), and the main process contains proc(x),
		##   a is replaced with x, so replacedVars[a] = x
		self.typeCheckStrBuilder = u"Rules used: \n◻\n"
		self.tcStrIndent = ""
		self.tcErrorStrBuilder = ""
		self.gamma = {}
		self.gammaStack = [{}]
		self.exprGamma = {}
		self.typeNames = {}
		self.replacedVars = {}
		## THESE VARIABLES ARE USED FOR THE ENCODING
		## encodedStrBuilder is used to reconstruct the pi calc string.
		## encStrIndent is used to indent the typechecking output for improved readability
		## encErrorStrBuilder is used to construct error messages
		## encFunc is the encoding function f that renames variables in the encoding
		##   i.e. replaces subsequent instances of session endpoint x with linear channel c
		## contChanTypes is used to store the ANTLR context of the type of a given channel's current form
		##   i.e for channel x, contChanTypes[x] first contains the type of x, say ?T.S, then when x is used for some communication,
		##   contChanTypes[x] is updated to contain the updatedd type of x, i.e. S
		##   This is used to generate type annotations of continuation channels
		##   As such, the context stored gets encoded
		## contChanTypesStack stores copies of contChanTypes with different values for a particular channel
		##   This is used for branch statements, so the continuation of the channel for each branch can be stored
		## usedVarNames is a list of user-made variable names,
		##   collected by VariableNameCollector.py, used to prevent the encoding 
		##   from generating variables names that already exist in the code
		## branchStack is used to track when a process is part of a continuation of a branch
		## encFuncBackupStack is used to store older version of encFunc for different continuations of a branch
		##   When a branch is entered, a backup of encFunc is stored in encFuncBackupStack
		##   and a B is pushed, and as each new process is entered, a C is pushed
		##   When exiting a process, the top C is popped
		##   When a process is entered and the top element is B, the normal encoding is replaced with the backup encoding
		## varNamesBackupStack is used to store older copies of usedVarNames
		##   This is done so generateChannelName can reset back to c when this would not cause conflicts
		##   i.e. during different continuations of a branch statement, or the different processes in a composition
		## compStack is used similarly to branchStack, but for compositions
		self.encodedStrBuilder = ""
		self.encStrIndent = ""
		self.encStrIndent = ""
		self.encErrorStrBuilder = ""
		self.encFunc = {}
		self.contChanTypes = {}
		self.contChanTypesStack = []
		self.usedVarNames = varNameList
		self.branchStack = []
		self.encFuncBackupStack = []
		self.varNamesBackupStack = []
		self.compStack = []


	## Define custom errors, so that typechecking and encoding can be interrupted when an error in the user input is found.
	class typecheckException(Exception):
		pass

	class encodingException(Exception):
		pass


	## Walk the supplied parse tree to perform the operations requested by the webapp
	## Also performs error handling so webapp responds when exception occurs
	def doOperations(self, parseTree):
		try:
			walker = ParseTreeWalker()
			walker.walk(self, parseTree)
		except (self.typecheckException, self.encodingException):
			pass


	## Supplementary functions for typechecking

	# Augment a context with additional name-type pairs without changing original context
	# i.e. return resulting context of G, x:T1, y:T2
	# gamma and aug should both be dictionaries, 
	# gamma corresponding to G, aug corresponding to x:T1, y:T2
	def augmentGamma(self, gamma, aug):
		augGamma = {}
		for (key, value) in gamma.items():
			augGamma[key] = value
		for (key, value) in aug.items():
			augGamma[key] = value
		return augGamma

	# Given a session-typed gamma G, creates two new gammas G1 and G2, such that G1 ◦ G2 = G
	# g1LinList is a list of variables names that, if in G and are of linear type, should be placed in G1
	# All other linear typed variables are placed in G2
	def splitGamma(self, gamma, g1LinList=[]):
		gamma1 = {}
		gamma2 = {}
		for (varName, varType) in gamma.items():
			if self.sesLinType(varType):
				if varName in g1LinList:
					gamma1[varName] = varType
				else:
					gamma2[varName] = varType
			else:
				gamma1[varName] = varType
				gamma2[varName] = varType
		return (gamma1, gamma2)

	# Given a session type t, return True if lin(t), false if un(t)
	def sesLinType(self, varType):
		if isinstance(varType, PiCalcParser.SendContext) or isinstance(varType, PiCalcParser.ReceiveContext) or isinstance(varType, PiCalcParser.SelectContext) or isinstance(varType, PiCalcParser.BranchContext):
			return True

	# Given a session-typed context gamma, return True if lin(gamma), false if un(gamma)
	def sesLinGamma(self, gamma):
		for v in gamma.values():
			if self.sesLinType(v):
				return True
		return False

	# Given an ANTLR context of a session type, produce a context of the dual type
	def getSesTypeDual(self, typeCtx):
		typeStr = typeCtx.getText()
		dualStr = ""
		parenLayers = 0
		for i in range(len(typeStr)):
			if typeStr[i] == "(":
				parenLayers += 1
				dualStr = dualStr + "("
			elif typeStr[i] == ")":
				parenLayers -= 1
				dualStr = dualStr + ")"
			elif typeStr[i] == "!" and parenLayers == 0:
				dualStr = dualStr + "?"
			elif typeStr[i] == "?" and parenLayers == 0:
				dualStr = dualStr + "!"
			elif typeStr[i] == "+" and parenLayers == 0:
				dualStr = dualStr + "&"
			elif typeStr[i] == "&" and parenLayers == 0:
				dualStr = dualStr + "+"
			else:
				dualStr = dualStr + typeStr[i]
		# dualStr = typeStr.translate(dict(zip([ord(char) for char in u"?!&+"], [ord(char) for char in u"!?+&"])))
		inStrm = InputStream(dualStr)
		lex = PiCalcLexer(inStrm)
		tknStrm = CommonTokenStream(lex)
		par = PiCalcParser(tknStrm)
		return par.sType()

	# Given an ANTLR context of a literal value, return the context of that literal's type
	def getBasicSesType(self, literalValue):
		inStrm = InputStream("")
		if isinstance(literalValue, PiCalcParser.IntegerValueContext):
			inStrm = InputStream("sInt")
		elif isinstance(literalValue, PiCalcParser.StringValueContext):
			inStrm = InputStream("sString")
		elif isinstance(literalValue, PiCalcParser.BooleanValueContext):
			inStrm = InputStream("sBool")
		elif isinstance(literalValue, PiCalcParser.UnitValueContext):
			inStrm = InputStream("sUnit")
		elif isinstance(literalValue, PiCalcParser.ExprValueContext):
			expr = literalValue.expression()
			if isinstance(expr, PiCalcParser.StrConcatContext):
				inStrm = InputStream("sString")
			elif (
				isinstance(expr, PiCalcParser.IntAddContext) or isinstance(expr, PiCalcParser.IntSubContext) or isinstance(expr, PiCalcParser.IntMultContext) or 
				isinstance(expr, PiCalcParser.IntDivContext) or isinstance(expr, PiCalcParser.IntModContext)
			):
				inStrm = InputStream("sInt")
			elif (
				isinstance(expr, PiCalcParser.EqlContext) or isinstance(expr, PiCalcParser.InEqlContext) or isinstance(expr, PiCalcParser.IntGTContext) or 
				isinstance(expr, PiCalcParser.IntGTEqContext) or isinstance(expr, PiCalcParser.IntLTContext) or isinstance(expr, PiCalcParser.IntLTEqContext) or 
				isinstance(expr, PiCalcParser.BoolNotContext) or isinstance(expr, PiCalcParser.BoolAndContext) or isinstance(expr, PiCalcParser.BoolOrContext) or 
				isinstance(expr, PiCalcParser.BoolXorContext)
			):
				inStrm = InputStream("sBool")
		lex = PiCalcLexer(inStrm)
		tknStrm = CommonTokenStream(lex)
		par = PiCalcParser(tknStrm)
		return par.basicSType()

	# Given a linear-typed gamma G, creates two new gammas G1 and G2 such that G1 u G2 = G
	# g1LinList is a list of tuples of variables names and capabilities that, if in G and are of linear type, should be placed in G1
	# All other linear typed variables are placed in G2
	# If a variable is a linear connection, its capabilities are split, 
	# and the capability in the tuple is checked to see which capability goes in G1, and the other goes in G2
	def combineGamma(self, gamma, g1LinList=[]):
		gamma1 = {}
		gamma2 = {}
		capabilities = dict(g1LinList)
		for (varName, varType) in gamma.items():
			if self.linLinType(varType):
				if varName not in gamma1:
					if varName in capabilities:
						if capabilities[varName] == "Both" and not isinstance(varType, PiCalcParser.LinearConnectionContext):
							gamma1[varName] = varType
							gamma1[varName + u"▼"] = gamma[varName + u"▼"]
						elif isinstance(varType, PiCalcParser.LinearConnectionContext):
							if capabilities[varName] == "Both":
								gamma1[varName] = varType
							else:
								(varTypeIn, varTypeOut) = self.splitCapabilities(varType)
								if capabilities[varName] == "Input":
									gamma1[varName] = varTypeIn
									gamma2[varName] = varTypeOut
								elif capabilities[varName] == "Output":
									gamma1[varName] = varTypeOut
									gamma2[varName] = varTypeIn
						else:
							gamma1[varName] = varType
					elif u"▼" in varName and varName[:-1] in capabilities and capabilities[varName[:-1]] == "Both":
						gamma1[varName] = varType
						gamma1[varName[:-1]] = gamma[varName[:-1]]
					else:
						gamma2[varName] = varType
			else:
				gamma1[varName] = varType
				gamma2[varName] = varType
		return (gamma1, gamma2)

	# Given a linType t, return True if lin(t), false if un(t)
	def linLinType(self, varType):
		if isinstance(varType, PiCalcParser.LinearOutputContext) or isinstance(varType, PiCalcParser.LinearInputContext) or isinstance(varType, PiCalcParser.LinearConnectionContext):
			return True
		if isinstance(varType, PiCalcParser.VariantTypeContext):
			for i in range(len(varType.conts)):
				if isinstance(varType.conts[i], PiCalcParser.LinearOutputContext) or isinstance(varType.conts[i], PiCalcParser.LinearInputContext) or isinstance(varType.conts[i], PiCalcParser.LinearConnectionContext):
					return True

	# Given a linear-typed context gamma, return True if lin(gamma), false if un(gamma)
	def linLinGamma(self, gamma):
		for v in gamma.values():
			if self.linLinType(v):
				return True
		return False

	# Given an ANTLR context of a linear connection, return the contexts for the separated input and output capabilities.
	def splitCapabilities(self, linCon):
		linConStr = linCon.getText()
		linInStr = "li" + linConStr[2:]
		linOutStr = "lo" + linConStr[2:]
		inStrmIn = InputStream(linInStr)
		lexIn = PiCalcLexer(inStrmIn)
		tknStrmIn = CommonTokenStream(lexIn)
		parIn = PiCalcParser(tknStrmIn)
		inStrmOut = InputStream(linOutStr)
		lexOut = PiCalcLexer(inStrmOut)
		tknStrmOut = CommonTokenStream(lexOut)
		parOut = PiCalcParser(tknStrmOut)
		return (parIn.linearType(), parOut.linearType())

	# Given an ANTLR context of a literal value, return the context of that literal's type
	def getBasicLinType(self, literalValue):
		inStrm = InputStream("")
		if isinstance(literalValue, PiCalcParser.IntegerValueContext):
			inStrm = InputStream("lInt")
		elif isinstance(literalValue, PiCalcParser.StringValueContext):
			inStrm = InputStream("lString")
		elif isinstance(literalValue, PiCalcParser.BooleanValueContext):
			inStrm = InputStream("lBool")
		elif isinstance(literalValue, PiCalcParser.UnitValueContext):
			inStrm = InputStream("lUnit")
		elif isinstance(literalValue, PiCalcParser.ExprValueContext):
			expr = literalValue.expression()
			if isinstance(expr, PiCalcParser.StrConcatContext):
				inStrm = InputStream("lString")
			elif (
				isinstance(expr, PiCalcParser.IntAddContext) or isinstance(expr, PiCalcParser.IntSubContext) or isinstance(expr, PiCalcParser.IntMultContext) or 
				isinstance(expr, PiCalcParser.IntDivContext) or isinstance(expr, PiCalcParser.IntModContext)
			):
				inStrm = InputStream("lInt")
			elif (
				isinstance(expr, PiCalcParser.EqlContext) or isinstance(expr, PiCalcParser.InEqlContext) or isinstance(expr, PiCalcParser.IntGTContext) or 
				isinstance(expr, PiCalcParser.IntGTEqContext) or isinstance(expr, PiCalcParser.IntLTContext) or isinstance(expr, PiCalcParser.IntLTEqContext) or 
				isinstance(expr, PiCalcParser.BoolNotContext) or isinstance(expr, PiCalcParser.BoolAndContext) or isinstance(expr, PiCalcParser.BoolOrContext) or 
				isinstance(expr, PiCalcParser.BoolXorContext)
			):
				inStrm = InputStream("lBool")
		lex = PiCalcLexer(inStrm)
		tknStrm = CommonTokenStream(lex)
		par = PiCalcParser(tknStrm)
		return par.basicLType()

	# Given an ANTLR context of a linear type, produce a context of the dual type
	def getLinTypeDual(self, typeCtx):
		typeStr = typeCtx.getText()
		dualStr = typeStr[:2].translate(dict(zip([ord(char) for char in "io"], [ord(char) for char in "oi"]))) + typeStr[2:]
		inStrm = InputStream(dualStr)
		lex = PiCalcLexer(inStrm)
		tknStrm = CommonTokenStream(lex)
		par = PiCalcParser(tknStrm)
		return par.linearType()

	# Given an ANTLR context for a variable, retrieve the variable which has replaced it due to process naming
	def getReplacement(self, var):
		return self.replacedVars.get(var.getText(), var)


	# Given an ANTLR context for a variable, replace the next placeholder in the typeCheckStrBuilder with the rule for that value
	def printVariableTypeRule(self, varCtx, gamma):
		if isinstance(varCtx, PiCalcParser.NamedValueContext):
			if self.doSesTypeChecking:
				tempGamma = copy.deepcopy(gamma)
				del tempGamma[varCtx.getText()]
				if self.sesLinGamma(tempGamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Var (" + varCtx.getText() + ") failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-Var (" + varCtx.getText() + ")", 1)
			elif self.doLinTypeChecking:
				tempGamma = copy.deepcopy(gamma)
				del tempGamma[varCtx.getText()]
				if self.linLinGamma(tempGamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-Var (" + varCtx.getText() + ") failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var (" + varCtx.getText() + ")", 1)
		elif isinstance(varCtx, PiCalcParser.IntegerValueContext):
			if self.doSesTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Int failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-Int", 1)
			elif self.doLinTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-Int failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Int", 1)
		elif isinstance(varCtx, PiCalcParser.StringValueContext):
			if self.doSesTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-String failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-String", 1)
			elif self.doLinTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-String failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-String", 1)
		elif isinstance(varCtx, PiCalcParser.BooleanValueContext) and varCtx.getText() == "True":
			if self.doSesTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-True failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-True", 1)
			elif self.doLinTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-True failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-True", 1)
		elif isinstance(varCtx, PiCalcParser.BooleanValueContext) and varCtx.getText() == "False":
			if self.doSesTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-False failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-False", 1)
			elif self.doLinTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-False failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-False", 1)
		elif isinstance(varCtx, PiCalcParser.UnitValueContext):
			if self.doSesTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Val failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", "T-Val", 1)
			elif self.doLinTypeChecking:
				if self.sesLinGamma(gamma):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-Unit failed. Context is still linear.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Unit", 1)
		elif isinstance(varCtx, PiCalcParser.VariantValContext):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed due to " + varCtx.getText() + ". Variant values are not allowed in session-typed pi calculus.</span>\n"
				raise self.typecheckException
			if self.doLinTypeChecking:
				if varCtx.value().getText() not in gamma:
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + u"<span class='error'>ERROR: Typechecking rule Tπ-LVal (" + varCtx.getText() + ") failed. Variant value " + varCtx.variantVal().getText() + "'s channel " + varCtx.variantVal().value().getText() + "not in context.</span>\n"
					raise self.typecheckException
				else:
					self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-LVal (" + varCtx.getText() + ")", 1)
		elif isinstance(varCtx, PiCalcParser.ExprValueContext):
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"☆", 1)
			self.exprGamma = gamma


	def getTypeCheckResults(self):
		oldStr = self.typeCheckStrBuilder
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.translate({ord(c): None for c in u"◻"})
		if self.tcErrorStrBuilder == "" and self.encErrorStrBuilder == "":
			if oldStr != self.typeCheckStrBuilder:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: The typechecking encountered some kind of problem and could not be performed. Please check that your code is valid.</span>\n"
		if self.tcErrorStrBuilder != "" or self.encErrorStrBuilder != "":
			self.typeCheckStrBuilder = ""
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"▵", ", ")
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace("\n\n", "\n")
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace("<", "&lt;")
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(">", "&gt;")
			self.typeCheckStrBuilder = self.typeCheckStrBuilder + "<span class='success'>Typechecking successful.</span> "
		return (self.typeCheckStrBuilder, self.tcErrorStrBuilder)


	## Supplementary functions for encoding

	# Generate a new channel name for the encoding function
	def generateChannelName(self):
		chan = "c"
		while chan in self.usedVarNames:
			chan = chan + "'"
		self.usedVarNames.append(chan)
		return chan

	def encodeName(self, name):
		if name == "*":
			return "*"
		return self.encFunc.get(name, name)

	def checkBranchStack(self, isBranch):
		if self.branchStack != []:
			if self.branchStack[-1] != "B":
				if not(isBranch):
					self.branchStack.append("C")
			else:
				if self.encFuncBackupStack != []:
					self.encFunc = copy.deepcopy(self.encFuncBackupStack[-1])
				if self.varNamesBackupStack != []:
					self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])
				if self.contChanTypesStack != []:
					self.contChanTypes = copy.deepcopy(self.contChanTypesStack.pop())
				if not(isBranch):
					self.branchStack.append("C")

	def checkCompStack(self, isComp):
		if self.compStack != []:
			if self.compStack[-1] != "C":
				if not(isComp):
					self.compStack.append("P")
			else:
				if self.varNamesBackupStack != []:
					self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])
				if not(isComp):
					self.compStack.append("P")

	def getEncoding(self):
		# Attempt to remove any leftover placeholders, and display error if anything was removed
		oldStr = self.encodedStrBuilder
		self.encodedStrBuilder = self.encodedStrBuilder.translate({ord(c): None for c in u"◼▲▼●⬟"})
		if self.encErrorStrBuilder == "" and self.tcErrorStrBuilder == "":
			if (oldStr != self.encodedStrBuilder):
				self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: The encoding encountered some kind of problem and could not be performed. Please check that your code is valid.</span>\n"
		if self.encErrorStrBuilder != "" or self.tcErrorStrBuilder != "":
			self.encodedStrBuilder = ""
		return (self.encodedStrBuilder, self.encErrorStrBuilder)


	## LISTENER METHODS

	## Encoding explanation:
	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## ◼ represents placeholder type declarations,
	## ▲ represents placeholder type, ▼ represents a placeholder type's dual,
	## ● represents placeholder processes, ⬟ represents placeholder process name declarations


	## DECLARATIONS

	def enterDeclAndProcs(self, ctx):
		if self.doEncoding:
			self.enterDeclAndProcsEnc(ctx)
	# Place single decl placeholder and single process placeholder, separated by two newlines
	def enterDeclAndProcsEnc(self, ctx):
		if ctx.decls():
			self.encodedStrBuilder = u"◼\n\n●"
		else:
			self.encodedStrBuilder = u"●"

	def enterDecls(self, ctx):
		self.gammaStack.pop()
		if self.doEncoding:
			self.enterDeclsEnc(ctx)
	# Replace single decl placeholder as placed by enterDeclAndProcs above, with placeholders for each declaration
	def enterDeclsEnc(self, ctx):
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		if len(ctx.decs) > 1:
			decPlaceholderStr = ""
			for i in range(len(ctx.decs)):
				if i != (len(ctx.decs) - 1):
					decPlaceholderStr = decPlaceholderStr + u"◼,\n"
				else:
					decPlaceholderStr = decPlaceholderStr + u"◼\n"
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decPlaceholderStr, 1)
	
	def exitDecls(self, ctx):
		if self.doSesTypeChecking:
			self.exitDeclsSTCh(ctx)
		if self.doLinTypeChecking:
			self.exitDeclsLTCh(ctx)
		if self.doEncoding:
			self.exitDeclsEnc(ctx)
	def exitDeclsEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])
			self.varNamesBackupStack.pop()
	def exitDeclsSTCh(self, ctx):
		self.gammaStack.append(self.gamma)
	def exitDeclsLTCh(self, ctx):
		self.gammaStack.append(self.gamma)


	def enterVariableAssignment(self, ctx):
		if self.doEncoding:
			self.enterVariableAssignmentEnc(ctx)
		if self.doSesTypeChecking:
			self.enterVariableAssignmentSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterVariableAssignmentLTCh(ctx)
	# No type, so no change needed
	def enterVariableAssignmentEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", ctx.getText(), 1)
	def enterVariableAssignmentSTCh(self, ctx):
		if ctx.var.text not in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is assigned a value before being declared with a type.</span>\n"
			raise self.typecheckException
		else:
			valType = self.getBasicSesType(ctx.value())
			if not isinstance(valType, type(self.gamma[ctx.var.text])):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + self.gamma[ctx.var.text].getText() + ", but is being assigned a value of type " + valType.getText() + ".</span>\n"
				raise self.typecheckException
	def enterVariableAssignmentLTCh(self, ctx):
		if ctx.var.text not in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is assigned a value before being declared with a type.</span>\n"
			raise self.typecheckException
		else:
			valType = self.getBasicLinType(ctx.value())
			if not isinstance(valType, type(self.gamma[ctx.var.text])):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + self.gamma[ctx.var.text].getText() + ", but is being assigned a value of type " + valType.getText() + ".</span>\n"
				raise self.typecheckException
		


	def enterProcessNamingNmd(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingNmdEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.namedType()), copy.deepcopy(ctx.processPrim()))
		self.stateTest = copy.deepcopy((self.doSesTypeChecking, self.doLinTypeChecking, self.doEncoding))
		self.doSesTypeChecking = False
		self.doLinTypeChecking = False
		self.doEncoding = False
	# Save context for process naming for later
	def enterProcessNamingNmdEnc(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Process naming containing linear types is not supported in session-typed pi calculus.</span>\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.value().getText()] = fullType.sType()
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", u"⬟", 1)

	def exitProcessNamingNmd(self, ctx):
		(savedDSTCH, savedDLTCH, savedDEnc) = self.stateTest
		self.doSesTypeChecking = savedDSTCH
		self.doLinTypeChecking = savedDLTCH
		self.doEncoding = savedDEnc
		if self.doEncoding:
			self.exitProcessNamingSesEnc(ctx)
	def exitProcessNamingNmdEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterProcessNamingSes(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingSesEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.tType()), copy.deepcopy(ctx.processPrim()))
		self.stateTest = copy.deepcopy((self.doSesTypeChecking, self.doLinTypeChecking, self.doEncoding))
		self.doSesTypeChecking = False
		self.doLinTypeChecking = False
		self.doEncoding = False
	# Save context for process naming for later
	def enterProcessNamingSesEnc(self, ctx):
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.value().getText()] = ctx.tType()
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", u"⬟", 1)

	def exitProcessNamingSes(self, ctx):
		(savedDSTCH, savedDLTCH, savedDEnc) = self.stateTest
		self.doSesTypeChecking = savedDSTCH
		self.doLinTypeChecking = savedDLTCH
		self.doEncoding = savedDEnc
		if self.doEncoding:
			self.exitProcessNamingSesEnc(ctx)
	def exitProcessNamingSesEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterProcessNamingLin(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingLinEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.linearType()), copy.deepcopy(ctx.processPrim()))
		self.stateTest = copy.deepcopy((self.doSesTypeChecking, self.doLinTypeChecking, self.doEncoding))
		self.doSesTypeChecking = False
		self.doLinTypeChecking = False
		self.doEncoding = False
	# Raise error if linear version of process naming is used in encoding
	def enterProcessNamingLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Process naming containing linear types is not supported in session-typed pi calculus.</span>\n"
		raise self.encodingException

	def exitProcessNamingLin(self, ctx):
		(savedDSTCH, savedDLTCH, savedDEnc) = self.stateTest
		self.doSesTypeChecking = savedDSTCH
		self.doLinTypeChecking = savedDLTCH
		self.doEncoding = savedDEnc


	def enterSessionTypeNaming(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionTypeNamingSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterSessionTypeNamingLTCh(ctx)
		if self.doEncoding:
			self.enterSessionTypeNamingEnc(ctx)
	# Place type placeholder
	def enterSessionTypeNamingEnc(self, ctx):
		self.typeNames[ctx.name.text] = ctx.tType()
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		decStr = "type " + ctx.name.text + u"' := ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterSessionTypeNamingSTCh(self, ctx):
		self.typeNames[ctx.name.text] = ctx.tType()
	def enterSessionTypeNamingLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Session type naming is not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitSessionTypeNaming(self, ctx):
		if self.doEncoding:
			self.exitSessionTypeNamingEnc(ctx)
	def exitSessionTypeNamingEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterNamedTypeDecl(self, ctx):
		if self.doSesTypeChecking:
			self.enterNamedTypeDeclSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterNamedTypeDeclLTCh(ctx)
		if self.doEncoding:
			self.enterNamedTypeDeclEnc(ctx)
	# Place type placeholder
	def enterNamedTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterNamedTypeDeclSTCh(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Type declaration contains undeclared type name.</span>\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType
	def enterNamedTypeDeclLTCh(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Type declaration contains undeclared type name.</span>\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType


	def enterNmdTypeDeclAndAssign(self, ctx):
		if self.doSesTypeChecking:
			self.enterNmdTypeDeclAndAssignSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterNmdTypeDeclAndAssignLTCh(ctx)
		if self.doEncoding:
			self.enterNmdTypeDeclAndAssignEnc(ctx)
	# Place type placeholder
	def enterNmdTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterNmdTypeDeclAndAssignSTCh(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Type declaration contains undeclared type name.</span>\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType
	def enterNmdTypeDeclAndAssignLTCh(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Type declaration contains undeclared type name.</span>\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType


	def enterSessionTypeDecl(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionTypeDeclSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterSessionTypeDeclLTCh(ctx)
		if self.doEncoding:
			self.enterSessionTypeDeclEnc(ctx)
	# Place type placeholder
	def enterSessionTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.var.text] = ctx.tType()
	def enterSessionTypeDeclSTCh(self, ctx):
		if isinstance(ctx.tType(), PiCalcParser.BasicSesTypeContext):
			self.gamma[ctx.var.text] = ctx.tType().basicSType()
		else:
			self.gamma[ctx.var.text] = ctx.tType()
	def enterSessionTypeDeclLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Session type declarations are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException


	def enterSesTypeDeclAndAssign(self, ctx):
		if self.doSesTypeChecking:
			self.enterSesTypeDeclAndAssignSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterSesTypeDeclAndAssignLTCh(ctx)
		if self.doEncoding:
			self.enterSesTypeDeclAndAssignEnc(ctx)
	# Place type placeholder
	def enterSesTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.var.text] = ctx.tType()
	def enterSesTypeDeclAndAssignSTCh(self, ctx):
		if isinstance(ctx.tType(), PiCalcParser.BasicSesTypeContext):
			self.gamma[ctx.var.text] = ctx.tType().basicSType()
			valType = self.getBasicSesType(ctx.value())
			if not isinstance(valType, type(ctx.tType().basicSType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + ctx.tType() + ", but is being assigned a value of type " + valType + ".</span>\n"
				raise self.typecheckException
		else:
			self.gamma[ctx.var.text] = ctx.tType()
			valType = self.getBasicSesType(ctx.value())
			if not isinstance(valType, type(ctx.tType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + ctx.tType() + ", but is being assigned a value of type " + valType + ".</span>\n"
				raise self.typecheckException
	def enterSesTypeDeclAndAssignLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Session type declarations found in linear-typed pi calculus.</span>\n"
		raise self.typecheckException


	def enterLinearTypeNaming(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinearTypeNamingLTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeNamingEnc(ctx)
	def enterLinearTypeNamingEnc(self, ctx):
		decStr = "type " + ctx.name.text + " := " + ctx.linearType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type naming found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinearTypeNamingSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type naming found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinearTypeNamingLTCh(self, ctx):
		self.typeNames[ctx.name.text] = ctx.linearType()


	def enterLinearTypeDecl(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinearTypeDeclLTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeDeclEnc(ctx)
	def enterLinearTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type declarations found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinearTypeDeclSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type declarations found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinearTypeDeclLTCh(self, ctx):
		if isinstance(ctx.linearType(), PiCalcParser.BasicLinTypeContext):
			self.gamma[ctx.var.text] = ctx.linearType().basicLType()
		else:
			self.gamma[ctx.var.text] = ctx.linearType()


	def enterLinTypeDeclAndAssign(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinTypeDeclAndAssignLTCh(ctx)
		if self.doEncoding:
			self.enterLinTypeDeclAndAssignEnc(ctx)
	def enterLinTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType.getText() + " = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type declarations found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinTypeDeclAndAssignSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Linear type declarations found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterLinTypeDeclAndAssignLTCh(self, ctx):
		if isinstance(ctx.linearType(), PiCalcParser.BasicLinTypeContext):
			self.gamma[ctx.var.text] = ctx.linearType().basicLType()
			valType = self.getBasicLinType(ctx.value())
			if not isinstance(valType, type(ctx.linearType().basicLType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + ctx.linearType() + ", but is being assigned a value of type " + valType + ".</span>\n"
				raise self.typecheckException
		else:
			self.gamma[ctx.var.text] = ctx.linearType()
			valType = self.getBasicLinType(ctx.value())
			if not isinstance(valType, type(ctx.linearType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. " + ctx.var.text + " is type " + ctx.linearType() + ", but is being assigned a value of type " + valType + ".</span>\n"
				raise self.typecheckException



	## PROCESSES

	def enterTermination(self, ctx):
		if self.doSesTypeChecking:
			self.enterTerminationSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterTerminationLTCh(ctx)
		if self.doEncoding:
			self.enterTerminationEnc(ctx)
	# Termination encoded homomorphically
	def enterTerminationEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "stop", 1)
	def enterTerminationSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if self.sesLinGamma(self.gamma):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Inact failed. Termination occurs while context is still linear.</span>\n"
			raise self.typecheckException
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Inact", 1)
	def enterTerminationLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if self.linLinGamma(self.gamma):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Inact failed. Termination occurs while context is still linear.</span>\n"
			raise self.typecheckException
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Inact", 1)


	def enterNamedProcess(self, ctx):
		(delayChan, delayType, delayProc) = self.delayedProcesses[ctx.name.text]
		if self.doSesTypeChecking:
			self.enterNamedProcessSTCh(ctx, delayChan, delayType, delayProc)
		if self.doLinTypeChecking:
			self.enterNamedProcessLTCh(ctx, delayChan, delayType, delayProc)
		if self.doEncoding:
			self.enterNamedProcessEnc(ctx, delayChan, delayType, delayProc)
		procWalker = ParseTreeWalker()
		procWalker.walk(self, delayType)
		procWalker.walk(self, delayProc)
	# Encode process name, and traverse stored subtrees of process name declaration
	def enterNamedProcessEnc(self, ctx, delayChan, delayType, delayProc):
		nmStr = self.encodeName(ctx.name.text) + "(" + self.encodeName(ctx.value().getText()) + ")"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", nmStr, 1)
		nmDecStr = self.encodeName(ctx.name.text) + "(" + self.encodeName(ctx.value().getText()) + u" : ▲) := ●"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"⬟", nmDecStr, 1)
		self.encFunc[delayChan.getText()] = self.encFunc[ctx.value().getText()]
	def enterNamedProcessSTCh(self, ctx, delayChan, delayType, delayProc):
		self.gamma = self.gammaStack.pop()
		if isinstance(delayType, PiCalcParser.NamedSTypeContext) or isinstance(delayType, PiCalcParser.NamedTTypeContext) or isinstance(delayType, PiCalcParser.NamedTypeContext):
			delayType = self.typeNames[delayType.getText()]
		if isinstance(delayType, PiCalcParser.SessionTypeContext):
			delayType = delayType.sType()
		if not isinstance(delayType, type(self.gamma.get(ctx.value().getText()))):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed due to " + ctx.value().getText() + ". Variable type used in named process does not match named process declaration.</span>\n"
			raise self.typecheckException
		else:
			self.replacedVars[delayChan.getText()] = ctx.value()
			self.gammaStack.append(self.gamma)
	def enterNamedProcessLTCh(self, ctx, delayChan, delayType, delayProc):
		self.gamma = self.gammaStack.pop()
		if isinstance(delayType, PiCalcParser.NamedLinTypeContext) or isinstance(delayType, PiCalcParser.NamedTypeContext):
			delayType = self.typeNames[delayType.getText()]
		if not isinstance(delayType, type(self.gamma.get(ctx.value().getText()))):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed due to " + ctx.value().getText() + ". Variable type used in named process does not match named process declaration.</span>\n"
			raise self.typecheckException
		else:
			self.replacedVars[delayChan.getText()] = ctx.value()
			self.gammaStack.append(self.gamma)


	def enterOutput(self, ctx):
		if self.doSesTypeChecking:
			self.enterOutputSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterOutputLTCh(ctx)
		if self.doEncoding:
			self.enterOutputEnc(ctx)
	# Create new channel and send alongside encoded payload
	def enterOutputEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		if isinstance(self.contChanTypes[ctx.channel.getText()], PiCalcParser.ChannelTypeContext):
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "send(" + ctx.channel.getText() + ", " + ctx.payloads[0].getText() + u").●", 1)
		else:
			newChan = self.generateChannelName()
			newChanType = self.contChanTypes[ctx.channel.getText()].sType()
			self.contChanTypes[ctx.channel.getText()] = newChanType
			opStrBuilder = "(new " + newChan + u" : ▲) (send(" + self.encodeName(ctx.channel.getText())
			if (len(ctx.payloads)) > 1:
				self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Output processes containing multiple payloads are not supported in session-typed pi calculus.</span>\n"
				raise self.encodingException
			opStrBuilder = opStrBuilder + ", " + self.encodeName(ctx.payloads[0].getText()) + ", " + newChan + u").●)"
			self.encFunc[ctx.channel.getText()] = newChan
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", opStrBuilder, 1)
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType)
	def enterOutputSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		truePL = self.getReplacement(ctx.payloads[0])
		(gamma1, gamma2_3) = self.splitGamma(self.gamma, [trueChan.getText()])
		if (len(ctx.payloads)) > 1:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Out failed. Output processes containing multiple payloads are not supported in session-typed pi calculus.\n</span>"
			raise self.typecheckException
		(gamma2, gamma3) = self.splitGamma(gamma2_3, [truePL.getText()])
		chanType = gamma1.get(trueChan.getText())
		if isinstance(truePL, PiCalcParser.NamedValueContext):
			payloadType = gamma2.get(truePL.getText())
		## Handle literals and expressions
		else:
			payloadType = self.getBasicSesType(truePL)
		if isinstance(payloadType, PiCalcParser.BasicSesTypeContext):
			payloadType = payloadType.basicSType()
		elif isinstance(payloadType, PiCalcParser.SessionTypeContext):
			payloadType = payloadType.sType()
		if not isinstance(chanType, PiCalcParser.ChannelTypeContext):
			if not isinstance(chanType, PiCalcParser.SendContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Out failed due to " + trueChan.getText() + ". Output process on channel not of output type.</span>\n"
				raise self.typecheckException
			chanPLType = chanType.tType()
			if isinstance(chanPLType, PiCalcParser.BasicSesTypeContext):
				chanPLType = chanPLType.basicSType()
			elif isinstance(chanPLType, PiCalcParser.SessionTypeContext):
				chanPLType = chanPLType.sType()
			if not isinstance(payloadType, type(chanPLType)):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Out failed due to " + truePL.getText() + ". Output process payload does not match channel type.</span>\n"
				raise self.typecheckException
			else:
				augmentations = {trueChan.getText(): chanType.sType()}
				gamma3 = self.augmentGamma(gamma3, augmentations)
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵◻▵T-Out▵◻", 1)
				self.printVariableTypeRule(trueChan, gamma1)
				self.printVariableTypeRule(truePL, gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)
		else:
			chanPLType = chanType.tType()
			if isinstance(chanPLType, PiCalcParser.BasicSesTypeContext):
				chanPLType = chanPLType.basicSType()
			elif isinstance(chanPLType, PiCalcParser.SessionTypeContext):
				chanPLType = chanPLType.sType()
			if not isinstance(payloadType, type(chanPLType)):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-StndOut failed due to " + truePL.getText() + ". Output process payload does not match channel type.</span>\n"
				raise self.typecheckException
			else:
				augmentations = {trueChan.getText(): chanType}
				gamma3 = self.augmentGamma(gamma3, augmentations)
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵◻▵T-StndOut▵◻", 1)
				self.printVariableTypeRule(trueChan, gamma1)
				self.printVariableTypeRule(truePL, gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)
	def enterOutputLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		truePLs = [self.getReplacement(pl) for pl in ctx.payloads]
		(gamma1, gamma2_3) = self.combineGamma(self.gamma, [(trueChan.getText(), "Output")])
		plCaps = []
		for pl in truePLs:
			if pl.getText() + u"▼" in gamma2_3:
				plCaps.append((pl.getText() + u"▼", ""))
			else:
				plCaps.append((pl.getText(), ""))
		(gamma2, gamma3) = self.combineGamma(gamma2_3, plCaps)
		## Remove dual triangle from variables in gamma2
		for name in gamma2.keys():
			if u"▼" in name:
				gamma2[name[:-1]] = gamma2[name]
				del gamma2[name]
		gamma2lst = [[] for i in range(len(truePLs))]
		gamma2lst[0] = gamma2
		for i in range(len(truePLs)-1):
			(gamma2lst[i], gamma2lst[i+1]) = self.combineGamma(gamma2lst[i], [(truePLs[i].getText(), "")])
		chanType = gamma1.get(trueChan.getText())
		payloadTypes = [[] for i in range(len(truePLs))]
		for i in range(len(truePLs)):
			if isinstance(truePLs[i], PiCalcParser.NamedValueContext):
				payloadTypes[i] = gamma2lst[i].get(truePLs[i].getText())
			## Handle literals and expressions
			else:
				payloadTypes[i] = self.getBasicLinType(truePLs[i])
			if isinstance(payloadTypes[i], PiCalcParser.BasicLinTypeContext):
				payloadTypes[i] = payloadTypes[i].basicLType()
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearOutputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Out failed due to " + trueChan.getText() + ". Output process on channel not of output type.</span>\n"
				raise self.typecheckException
			else:
				chanPLTypes = chanType.payloads
				for i in range(len(payloadTypes)):
					if isinstance(chanPLTypes[i], PiCalcParser.BasicLinTypeContext):
						chanPLTypes[i] = chanPLTypes[i].basicLType()
					if not isinstance(payloadTypes[i], type(chanPLTypes[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Out failed due to " + truePLs[i].getText() + ". Output process payload does not match channel type.</span>\n"
						raise self.typecheckException
				self.gammaStack.append(gamma3)
				tcLinOutStrBuilder = u"◻▵"
				for i in range(len(truePLs)):
					tcLinOutStrBuilder = tcLinOutStrBuilder + u"◻▵"
				tcLinOutStrBuilder = tcLinOutStrBuilder + u"Tπ-Out▵◻"
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", tcLinOutStrBuilder, 1)
				self.printVariableTypeRule(trueChan, gamma1)
				for i in range(len(truePLs)):
					self.printVariableTypeRule(truePLs[i], gamma2lst[i])
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)
		else:
			chanPLTypes = chanType.payloads
			for i in range(len(payloadTypes)):
				if isinstance(chanPLTypes[i], PiCalcParser.BasicLinTypeContext):
					chanPLTypes[i] = chanPLTypes[i].basicLType()
				if not isinstance(payloadTypes[i], type(chanPLTypes[i])):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-StndOut failed due to " + truePLs[i].getText() + ". Output process payload does not match channel type.</span>\n"
					raise self.typecheckException
			augmentations = {trueChan.getText(): chanType}
			gamma3 = self.augmentGamma(gamma3, augmentations)
			self.gammaStack.append(gamma3)
			tcLinOutStrBuilder = u"◻▵"
			for i in range(len(truePLs)):
				tcLinOutStrBuilder = tcLinOutStrBuilder + u"◻▵"
			tcLinOutStrBuilder = tcLinOutStrBuilder + u"Tπ-StndOut▵◻"
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", tcLinOutStrBuilder, 1)
			self.printVariableTypeRule(trueChan, gamma1)
			for pl in truePLs:
				self.printVariableTypeRule(pl, gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)

	def exitOutput(self, ctx):
		if self.doEncoding:
			self.exitOutputEnc(ctx)
	def exitOutputEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	# Output of variants, such as encoding of select, uses separate rule to allow for type annotations
	def enterOutputVariants(self, ctx):
		if self.doEncoding:
			self.enterOutputVariantsEnc(ctx)
		if self.doSesTypeChecking:
			self.enterOutputVariantsSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterOutputVariantsLTCh(ctx)
	def enterOutputVariantsEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Variant values found in session-typed pi calculus.</span>\n"
		raise self.encodingException
	def enterOutputVariantsSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Variant values found in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterOutputVariantsLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		truePLs = [self.getReplacement(pl) for pl in ctx.payloads]
		(gamma1, gamma2_3) = self.combineGamma(self.gamma, [(trueChan.getText(), "Output")])
		plCaps = []
		for i in range(len(truePLs)):
			gamma2_3[truePLs[i].getText()] = ctx.plTypes[i]
			plCaps.append((truePLs[i].getText(), ""))
			if (truePLs[i].getText() + u"▼").split("_")[1] in gamma2_3:
				plCaps.append(((truePLs[i].getText() + u"▼").split("_")[1], ""))
		(gamma2, gamma3) = self.combineGamma(gamma2_3, plCaps)
		## Remove dual triangle from variables in gamma2
		for name in gamma2.keys():
			if u"▼" in name:
				gamma2[name[:-1]] = gamma2[name]
				del gamma2[name]
		chanType = gamma1.get(trueChan.getText())
		payloadTypes = [[] for i in range(len(truePLs))]
		for i in range(len(truePLs)):
			payloadTypes[i] = ctx.plTypes[i]
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearOutputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking Tπ-Out failed due to " + trueChan.getText() + ". Output process on channel not of output type.</span>\n"
				raise self.typecheckException
			else:
				for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payloads[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Out failed due to " + truePLs[i].getText() + ". Output process payload does not match channel type.</span>\n"
						raise self.typecheckException
				self.gammaStack.append(gamma3)
				tcLinOutStrBuilder = u"◻▵"
				for i in range(len(truePLs)):
					tcLinOutStrBuilder = tcLinOutStrBuilder + u"◻▵"
				tcLinOutStrBuilder = tcLinOutStrBuilder + u"Tπ-Out▵◻"
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", tcLinOutStrBuilder, 1)
				self.printVariableTypeRule(trueChan, gamma1)
				for pl in truePLs:
					self.printVariableTypeRule(pl, gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)
		else:
			for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payloads[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-StndOut failed due to " + truePLs[i].getText() + ". Output process payload does not match channel type.</span>\n"
						raise self.typecheckException
			augmentations = {trueChan.getText(): chanType}
			gamma3 = self.augmentGamma(gamma3, augmentations)
			self.gammaStack.append(gamma3)
			tcLinOutStrBuilder = u"◻▵"
			for i in range(len(truePLs)):
				tcLinOutStrBuilder = tcLinOutStrBuilder + u"◻▵"
			tcLinOutStrBuilder = tcLinOutStrBuilder + u"Tπ-StndOut▵◻"
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", tcLinOutStrBuilder, 1)
			self.printVariableTypeRule(trueChan, gamma1)
			for pl in truePLs:
				self.printVariableTypeRule(pl, gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻", 1)


	def enterInputSes(self, ctx):
		if self.doSesTypeChecking:
			self.enterInputSesSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterInputSesLTCh(ctx)
		if self.doEncoding:
			self.enterInputSesEnc(ctx)
	# Receive new channel alongside payloads
	# ★ used so type annotations appear in correct order
	def enterInputSesEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		if isinstance(self.contChanTypes[ctx.channel.getText()], PiCalcParser.ChannelTypeContext):
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "receive(" + ctx.channel.getText() + ", " + ctx.payload.getText() + u" : ▲).●", 1)
		else:
			ipStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + ", " + ctx.payload.getText() + u" : ★"
			newChan = self.generateChannelName()
			newChanType = self.contChanTypes[ctx.channel.getText()].sType()
			self.contChanTypes[ctx.channel.getText()] = newChanType
			if isinstance(ctx.plType, PiCalcParser.SessionTypeContext):
				self.contChanTypes[ctx.payload.getText()] = ctx.plType.sType()
			elif isinstance(ctx.plType, PiCalcParser.ChannelTypeContext):
				self.contChanTypes[ctx.payload.getText()] = ctx.plType
			ipStrBuilder = ipStrBuilder + ", " + newChan + u" : ▲).●"
			self.encFunc[ctx.channel.getText()] = newChan
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", ipStrBuilder, 1)
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType)
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"★", u"▲", 1)
	def enterInputSesSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		truePL = self.getReplacement(ctx.payload)
		(gamma1, gamma2) = self.splitGamma(self.gamma, [trueChan.getText()])
		chanType = gamma1.get(trueChan.getText())
		payloadType = ctx.tType()
		if isinstance(payloadType, PiCalcParser.BasicSesTypeContext):
			payloadType = payloadType.basicSType()
		elif isinstance(payloadType, PiCalcParser.SessionTypeContext):
			payloadType = payloadType.sType()
		if not isinstance(chanType, PiCalcParser.ChannelTypeContext):
			if not isinstance(chanType, PiCalcParser.ReceiveContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder = "<span class='error'>ERROR: Typechecking rule T-In failed due to " + trueChan.getText() + ". Input process on channel not of receive type.</span>\n"
				raise self.typecheckException
			chanPLType = chanType.tType()
			if isinstance(chanPLType, PiCalcParser.BasicSesTypeContext):
				chanPLType = chanPLType.basicSType()
			elif isinstance(chanPLType, PiCalcParser.SessionTypeContext):
				chanPLType = chanPLType.sType()
			if not isinstance(payloadType, type(chanPLType)):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder = "<span class='error'>ERROR: Typechecking rule T-In failed due to " + truePL.getText() + ". Input process payload has type annotation that does not match channel type.</span>\n"
				raise self.typecheckException
			else:
				augmentations = {trueChan.getText(): chanType.sType(), truePL.getText(): chanPLType}
				gamma2 = self.augmentGamma(gamma2, augmentations)
				self.gammaStack.append(gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵T-In▵◻", 1)
				self.printVariableTypeRule(trueChan, gamma1)
		else:
			chanPLType = chanType.tType()
			if isinstance(chanPLType, PiCalcParser.BasicSesTypeContext):
				chanPLType = chanPLType.basicSType()
			elif isinstance(chanPLType, PiCalcParser.SessionTypeContext):
				chanPLType = chanPLType.sType()
			if not isinstance(payloadType, type(chanPLType)):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder = "<span class='error'>ERROR: Typechecking rule T-StndIn failed due to " + ctx.payload.getText() + ". Input process payload has type annotation that does not match channel type.</span>\n"
				raise self.typecheckException
			else:
				augmentations = {trueChan.getText(): chanType, truePL.getText(): chanPLType}
				gamma2 = self.augmentGamma(gamma2, augmentations)
				self.gammaStack.append(gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵T-StndIn▵◻", 1)
				self.printVariableTypeRule(trueChan, gamma1)
	def enterInputSesLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Input processes containing session types are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitInputSes(self, ctx):
		if self.doEncoding:
			self.exitInputSesEnc(ctx)
	def exitInputSesEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterInputLin(self, ctx):
		if self.doSesTypeChecking:
			self.enterInputLinSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterInputLinLTCh(ctx)
		if self.doEncoding:
			self.enterInputLinEnc(ctx)
	# Raise error if linear version of input is used in encoding
	def enterInputLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Input processes containing linear types and/or multiple payloads are not supported in session-typed pi calculus.</span>\n"
		raise self.encodingException
	def enterInputLinSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Input processes containing linear types and/or multiple payloads are not supported in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterInputLinLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		truePLs = [self.getReplacement(pl) for pl in ctx.payloads]
		(gamma1, gamma2) = self.combineGamma(self.gamma, [(trueChan.getText(), "Input")])
		chanType = gamma1.get(trueChan.getText())
		payloadTypes = copy.deepcopy(ctx.plTypes)
		for i in range(len(payloadTypes)):
			if isinstance(payloadTypes[i], PiCalcParser.BasicLinTypeContext):
				payloadTypes[i] = payloadTypes[i].basicLType()
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearInputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Inp failed due to " + trueChan.getText() + ". Input process on channel not of input type.</span>\n"
				raise self.typecheckException
			else:
				augmentations = {}
				chanPLTypes = chanType.payloads
				for i in range(len(payloadTypes)):
					if isinstance(chanPLTypes[i], PiCalcParser.BasicLinTypeContext):
						chanPLTypes[i] = chanPLTypes[i].basicLType()
					if not isinstance(payloadTypes[i], type(chanPLTypes[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Inp failed due to " + truePLs[i].getText() + ". Input process payload has type annotation that does not match channel type.</span>\n"
						raise self.typecheckException
					augmentations[truePLs[i].getText()] = chanPLTypes[i]
				gamma2 = self.augmentGamma(gamma2, augmentations)
				self.gammaStack.append(gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵Tπ-Inp▵◻", 1)
				self.printVariableTypeRule(trueChan, gamma1)
		else:
			augmentations = {trueChan.getText(): chanType}
			chanPLTypes = chanType.payloads
			for i in range(len(payloadTypes)):
				if isinstance(chanPLTypes[i], PiCalcParser.BasicLinTypeContext):
					chanPLTypes[i] = chanPLTypes[i].basicLType()
				if not isinstance(payloadTypes[i], type(chanPLTypes[i])):
					self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-StndInp failed due to " + truePLs[i].getText() + ". Input process payload has type annotation that does not match channel type.</span>\n"
					raise self.typecheckException
				augmentations[truePLs[i].getText()] = chanPLTypes[i]
			gamma2 = self.augmentGamma(gamma2, augmentations)
			self.gammaStack.append(gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵Tπ-StndInp▵◻", 1)
			self.printVariableTypeRule(trueChan, gamma1)



	def enterSelection(self, ctx):
		if self.doSesTypeChecking:
			self.enterSelectionSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterSelectionLTCh(ctx)
		if self.doEncoding:
			self.enterSelectionEnc(ctx)
	# Create new channel and send as variant value
	# ★ used so type annotations appear in correct order
	def enterSelectionEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		newChan = self.generateChannelName()
		newChanType = self.contChanTypes[ctx.channel.getText()]
		selStrBuilder = "(new " + newChan + u" : ★) (\n" + self.encStrIndent + "send(" + self.encodeName(ctx.channel.getText()) + "," + ctx.selection.getText() + "_" + newChan + " : <\n"
		self.encStrIndent = self.encStrIndent + "  "
		for i in range(len(newChanType.opts)):
			selStrBuilder = selStrBuilder + self.encStrIndent + newChanType.opts[i].getText() +  u"_▲"
			if i != len(newChanType.opts)-1:
				selStrBuilder = selStrBuilder + ", \n"
		selStrBuilder = selStrBuilder + u">).\n" + self.encStrIndent[:-2] + u"●)"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", selStrBuilder, 1)
		self.encStrIndent = self.encStrIndent[:-2]
		for i in range(len(newChanType.conts)):
			self.encStrIndent = self.encStrIndent + "  "
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType.conts[i])
			self.encStrIndent = self.encStrIndent[:-2]
			if newChanType.opts[i].getText() == ctx.selection.getText():
				self.encodedStrBuilder = self.encodedStrBuilder.replace(u"★", u"▲", 1)
				self.contChanTypes[ctx.channel.getText()] = newChanType.conts[i]
				typeWalker.walk(self, newChanType.conts[i])
	def enterSelectionSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		trueSel = self.getReplacement(ctx.selection)
		(gamma1, gamma2) = self.splitGamma(self.gamma, [trueChan.getText()])
		chanType = gamma1.get(trueChan.getText())
		if not isinstance(chanType, PiCalcParser.SelectContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Sel failed due to " + trueChan.getText() + ". Select process on channel not of select type.</span>\n"
			raise self.typecheckException
		else:
			for i in range(len(chanType.opts)):
				if chanType.opts[i].getText() == trueSel.getText():
					selType = chanType.conts[i]
			gamma2 = self.augmentGamma(gamma2, {trueChan.getText(): selType})
			self.gammaStack.append(gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"◻▵T-Sel▵◻", 1)
			self.printVariableTypeRule(trueChan, gamma1)
	def enterSelectionLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Select processes are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitSelection(self, ctx):
		if self.doEncoding:
			self.exitSelectionEnc(ctx)
	def exitSelectionEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterBranching(self, ctx):
		if self.doSesTypeChecking:
			self.enterBranchingSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterBranchingLTCh(ctx)
		if self.doEncoding:
			self.enterBranchingEnc(ctx)
	# Receive value then use for case statement
	def enterBranchingEnc(self, ctx):
		self.checkBranchStack(True)
		self.checkCompStack(False)
		caseVar = self.generateChannelName()
		caseVarType = self.contChanTypes[ctx.channel.getText()]
		for i in range(len(caseVarType.conts)-1, -1, -1):
			cctCopy = copy.deepcopy(self.contChanTypes)
			cctCopy[ctx.channel.getText()] = caseVarType.conts[i]
			self.contChanTypesStack.append(cctCopy)
		self.encStrIndent = self.encStrIndent + "  "
		brnStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + "," + caseVar + " : <\n"
		for i in range(len(caseVarType.opts)):
			brnStrBuilder = brnStrBuilder + self.encStrIndent + caseVarType.opts[i].getText() + u"_▲"
			if i != len(caseVarType.opts)-1:
				brnStrBuilder = brnStrBuilder + ", \n"
		brnStrBuilder = brnStrBuilder + ">).\n" + self.encStrIndent[:-2] + "case " + caseVar + " of { \n"
		newChan = self.generateChannelName()
		for i in range(len(ctx.opts)):
			brnStrBuilder = brnStrBuilder + self.encStrIndent + ctx.opts[i].getText() + "_(" + newChan + u" : ▲)" + " > \n" + self.encStrIndent + u"●"
			if i != (len(ctx.opts) - 1):
				brnStrBuilder = brnStrBuilder + ", \n"
			else:
				brnStrBuilder = brnStrBuilder + " }"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encFuncBackupStack.append(copy.deepcopy(self.encFunc))
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		self.branchStack.append("B")
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", brnStrBuilder, 1)
		for i in range(2):
			for i in range(len(caseVarType.conts)):
				typeWalker = ParseTreeWalker()
				typeWalker.walk(self, caseVarType.conts[i])
	def enterBranchingSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueChan = self.getReplacement(ctx.channel)
		trueOps = [self.getReplacement(op) for op in ctx.opts]
		(gamma1, gamma2) = self.splitGamma(self.gamma, [trueChan.getText()])
		chanType = gamma1.get(trueChan.getText())
		if not isinstance(chanType, PiCalcParser.BranchContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Brch failed due to " + trueChan.getText() + ". Branch process on channel not of branch type.</span>\n"
			raise self.typecheckException
		else:
			for i in range(len(chanType.conts)-1, -1, -1):
				brchGamma = self.augmentGamma(gamma2, {trueChan.getText(): chanType.conts[i]})
				self.gammaStack.append(brchGamma)
			self.tcStrIndent = self.tcStrIndent + "  "
			brchTcStrBuilder = u"◻▵T-Brch\n" + self.tcStrIndent + "{"
			for i in range(len(trueOps)):
				brchTcStrBuilder = brchTcStrBuilder + trueOps[i].getText() + u" : ◻"
				if i != (len(trueOps) -1):
					brchTcStrBuilder = brchTcStrBuilder + ";\n" + self.tcStrIndent
				else:
					self.tcStrIndent = self.tcStrIndent[:-2]
					brchTcStrBuilder = brchTcStrBuilder + "}\n" + self.tcStrIndent
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", brchTcStrBuilder, 1)
			self.printVariableTypeRule(trueChan, gamma1)
	def enterBranchingLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Branch processes are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitBranching(self, ctx):
		if self.doEncoding:
			self.exitBranchingEnc(ctx)
	def exitBranchingEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()
		if self.encFuncBackupStack != []:
			self.encFuncBackupStack.pop()
		if self.varNamesBackupStack != []:
			self.varNamesBackupStack.pop()


	def enterComposition(self, ctx):
		if self.doSesTypeChecking:
			self.enterCompositionSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterCompositionLTCh(ctx)
		if self.doEncoding:
			self.enterCompositionEnc(ctx)
	# Composition encoded homomorpically
	def enterCompositionEnc(self, ctx):
		self.checkCompStack(True)
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		self.compStack.append("C")
		self.encStrIndent = self.encStrIndent + "  "
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"( ●\n" + self.encStrIndent +  "|\n" + self.encStrIndent + u"● )", 1)
	def enterCompositionSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		procWalker = ParseTreeWalker()
		vnc = VariableNameCollector({})
		procWalker.walk(vnc, ctx.processPrim(0))
		channelList = vnc.getVarNameList()
		(gamma1, gamma2) = self.splitGamma(self.gamma, channelList)
		self.gammaStack.append(gamma2)
		self.gammaStack.append(gamma1)
		self.tcStrIndent = self.tcStrIndent + "  "
		compTcStrBuilder = "T-Par \n" + self.tcStrIndent
		compTcStrBuilder = compTcStrBuilder + u"(L: ◻ |\n" + self.tcStrIndent + u"R: ◻)\n" + self.tcStrIndent[:-2]
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", compTcStrBuilder, 1)
	def enterCompositionLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		procWalker = ParseTreeWalker()
		vnc = VariableNameCollector(self.delayedProcesses)
		procWalker.walk(vnc, ctx.processPrim(0))
		capList = vnc.getCapabilityList()
		(gamma1, gamma2) = self.combineGamma(self.gamma, capList)
		for name in gamma1:
			if name + u"▼" in gamma2:
				gamma2[name] = gamma2[name + u"▼"]
				del gamma2[name + u"▼"]
		self.gammaStack.append(gamma2)
		self.gammaStack.append(gamma1)
		self.tcStrIndent = self.tcStrIndent + "  "
		compTcStrBuilder = u"Tπ-Par \n" + self.tcStrIndent
		compTcStrBuilder = compTcStrBuilder + u"(L: ◻ |\n" + self.tcStrIndent + u"R: ◻)\n" + self.tcStrIndent[:-2]
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", compTcStrBuilder, 1)

	def exitComposition(self, ctx):
		if self.doEncoding:
			self.exitCompositionEnc(ctx)
	def exitCompositionEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]
		if self.compStack != []:
			self.compStack.pop()
		if self.varNamesBackupStack != []:
			self.varNamesBackupStack.pop()


	def enterSessionRestriction(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionRestrictionSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterSessionRestrictionLTCh(ctx)
		if self.doEncoding:
			self.enterSessionRestrictionEnc(ctx)
	# Create new channel to replace both endpoints
	def enterSessionRestrictionEnc(self, ctx):
		newChan = self.generateChannelName()
		for ep in ctx.endpoint:
			self.encFunc[ep.getText()] = newChan
		self.encStrIndent = self.encStrIndent + "  "
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "(new " + newChan + u" : ▲) (\n" + self.encStrIndent + u"●\n" + self.encStrIndent + ")", 1)
		if isinstance(ctx.sType(), PiCalcParser.NamedSTypeContext):
			if ctx.sType().getText() in self.typeNames:
				fullType = self.typeNames[ctx.sType().getText()]
				if isinstance(fullType, PiCalcParser.SessionTypeContext):
					self.contChanTypes[ctx.endpoint[0].getText()] = fullType.sType()
					self.contChanTypes[ctx.endpoint[1].getText()] = self.getSesTypeDual(fullType.sType())
		else:
			self.contChanTypes[ctx.endpoint[0].getText()] = ctx.sType()
			self.contChanTypes[ctx.endpoint[1].getText()] = self.getSesTypeDual(ctx.sType())
	def enterSessionRestrictionSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.endpoint[0].getText() in self.gamma or ctx.endpoint[1].getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Res failed due to " + ctx.endpoint[0].getText() + " or " + ctx.endpoint[1].getText() + ". Attempting to restrict variable name already in use.</span>\n"
			raise self.typecheckException
		augmentations = {}
		if isinstance(ctx.sType(), PiCalcParser.NamedSTypeContext):
			if ctx.sType().getText() in self.typeNames:
				fullType = self.typeNames[ctx.sType().getText()]
				if isinstance(fullType, PiCalcParser.SessionTypeContext):
					resType = fullType.sType()
		else:
			resType = ctx.sType()
		resTypeDual = self.getSesTypeDual(resType)
		augmentations[ctx.endpoint[0].getText()] = resType
		augmentations[ctx.endpoint[1].getText()] = resTypeDual
		newGamma = self.augmentGamma(self.gamma, augmentations)
		self.gammaStack.append(newGamma)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Res \n" + self.tcStrIndent + "[" + ctx.endpoint[0].getText() + " : " + resType.getText().replace(",", ", ") + ", \n" + self.tcStrIndent + ctx.endpoint[1].getText() + " : " + resTypeDual.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
	def enterSessionRestrictionLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Session restrictions are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitSessionRestriction(self, ctx):
		if self.doEncoding:
			self.exitSessionRestrictionEnc(ctx)
	def exitSessionRestrictionEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]


	def enterChannelRestrictionNmd(self, ctx):
		if self.doSesTypeChecking:
			self.enterChannelRestrictionNmdSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterChannelRestrictionNmdLTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionNmdEnc(ctx)
	# Channel Restriction encoded homomorphically
	def enterChannelRestrictionNmdEnc(self, ctx):
		fullType = self.typeNames.get(ctx.namedType().getText())
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Channel restrictions containing linear types are not supported in session pi calculus.</span>\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.value().getText()] = fullType
		self.encStrIndent = self.encStrIndent + "  "
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "(new " + ctx.value().getText() + u" : ▲) (\n" + self.encStrIndent + u"●\n" + self.encStrIndent + ")", 1)
	def enterChannelRestrictionNmdSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-StndRes failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			raise self.typecheckException
		fullType = self.typeNames.get(ctx.namedType().getText())
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Channel restrictions containing linear types are not supported in session pi calculus.</span>\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-StndRes failed due to " + ctx.value().getText() + ". Channel restriction on a session type.</span>\n"
			raise self.typecheckException
		newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : fullType})
		self.gammaStack.append(newGamma)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + fullType.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
	def enterChannelRestrictionNmdLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			if isinstance(fullType, PiCalcParser.NoCapabilityContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Res2 failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Res1 failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			raise self.typecheckException
		fullType = self.typeNames.get(ctx.namedType().getText())
		if isinstance(fullType, PiCalcParser.TTypeContext) or isinstance(fullType, PiCalcParser.STypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Channel restrictions containing session types are not supported in linear-typed pi calculus.</span>\n"
		elif isinstance(fullType, PiCalcParser.ConnectionContext):
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : fullType})
			self.gammaStack.append(newGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + fullType.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
		elif isinstance(fullType, PiCalcParser.NoCapabilityContext):
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : fullType})
			self.gammaStack.append(newGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Res2 \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + fullType.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
		else:
			typeAnnDual = self.getLinTypeDual(fullType)
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : fullType, ctx.value().getText() + u"▼" : typeAnnDual})
			self.gammaStack.append(newGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Res1 \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + fullType.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)

	def exitChannelRestrictionNmd(self, ctx):
		if self.doEncoding:
			self.exitChannelRestrictionNmdEnc(ctx)
	def exitChannelRestrictionNmdEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]


	def enterChannelRestrictionSes(self, ctx):
		if self.doSesTypeChecking:
			self.enterChannelRestrictionSesSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterChannelRestrictionSesLTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionSesEnc(ctx)
	# Channel Restriction encoded homomorphically
	def enterChannelRestrictionSesEnc(self, ctx):
		self.encStrIndent = self.encStrIndent + "  "
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"(new " + ctx.value().getText() + u" : ▲) (\n" + self.encStrIndent + u"●\n" + self.encStrIndent + ")", 1)
		self.contChanTypes[ctx.value().getText()] = ctx.tType()
	def enterChannelRestrictionSesSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-StndRes failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			raise self.typecheckException
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-StndRes failed due to " + ctx.value().getText() + ". Channel restriction on a session type.</span>\n"
			raise self.typecheckException
		newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : ctx.tType()})
		self.gammaStack.append(newGamma)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.tType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
	def enterChannelRestrictionSesLTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Channel restrictions containing session types are not supported in linear-typed pi calculus.</span>\n"
		raise self.typecheckException

	def exitChannelRestrictionSes(self, ctx):
		if self.doEncoding:
			self.exitChannelRestrictionSesEnc(ctx)
	def exitChannelRestrictionSesEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]


	def enterChannelRestrictionLin(self, ctx):
		if self.doSesTypeChecking:
			self.enterChannelRestrictionLinSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterChannelRestrictionLinLTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionLinEnc(ctx)
	# Raise error if linear version of channel restriction is used in encoding
	def enterChannelRestrictionLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Channel restrictions containing linear types are not supported in session-typed pi calculus.</span>\n"
		raise self.encodingException
	def enterChannelRestrictionLinSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Channel restrictions containing linear types are not supported in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterChannelRestrictionLinLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			if isinstance(ctx.linearType(), PiCalcParser.NoCapabilityContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Res2 failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Res1 failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.</span>\n"
			raise self.typecheckException
		if isinstance(ctx.linearType(), PiCalcParser.NoCapabilityContext):
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : ctx.linearType()})
			self.gammaStack.append(newGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Res2 \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.linearType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
		elif isinstance(ctx.linearType(), PiCalcParser.ConnectionContext):
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : ctx.linearType()})
			self.gammaStack.append(newGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.linearType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
		else:
			typeAnnDual = self.getLinTypeDual(ctx.linearType())
			newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : ctx.linearType(), ctx.value().getText() + u"▼" : typeAnnDual})
			self.gammaStack.append(newGamma)
			print(ctx.linearType().getText().replace(",", ", "))
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Res1 \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.linearType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)


	def enterCase(self, ctx):
		if self.doSesTypeChecking:
			self.enterCaseSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterCaseLTCh(ctx)
		if self.doEncoding:
			self.enterCaseEnc(ctx)
	def enterCaseEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Case processes not supported in session-typed pi calculus.</span>\n"
		raise self.encodingException
	def enterCaseSTCh(self, ctx):
		self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking failed. Case processes not supported in session-typed pi calculus.</span>\n"
		raise self.typecheckException
	def enterCaseLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		trueCase = self.getReplacement(ctx.case)
		trueOps = [self.getReplacement(op) for op in ctx.opts]
		(gamma1, gamma2) = self.combineGamma(self.gamma, [(trueCase.getText(), "")])
		caseType = gamma1.get(trueCase.getText())
		if not isinstance(caseType, PiCalcParser.VariantTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Case failed due to " + trueCase.getText() + ". Case statement with case variable not of variant type.</span>\n"
			raise self.typecheckException
		else:
			for i in range(len(caseType.conts)-1, -1, -1):
				caseGamma = self.augmentGamma(gamma2, {trueOps[i].value().getText(): caseType.conts[i]})
				self.gammaStack.append(caseGamma)
		self.tcStrIndent = self.tcStrIndent + "  "
		caseTcStrBuilder = u"◻▵Tπ-Case\n" + self.tcStrIndent + "{"
		for i in range(len(trueOps)):
			caseTcStrBuilder = caseTcStrBuilder + trueOps[i].ID().getText() + u" : ◻"
			if i != (len(trueOps) -1):
				caseTcStrBuilder = caseTcStrBuilder + ";\n" + self.tcStrIndent
			else:
				caseTcStrBuilder = caseTcStrBuilder + "}\n" + self.tcStrIndent[:-2]
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", caseTcStrBuilder, 1)
		self.printVariableTypeRule(trueCase, gamma1)



	## EXPRESSIONS

	# Given an ANTLR context for an expression with 2 operands, return the types of those two operands
	def getOperandTypes(self, exprCtx):
		if isinstance(exprCtx.value(0), PiCalcParser.NamedValueContext):
			val1Type = self.gamma.get(exprCtx.value(0).getText())
		else:
			if self.doSesTypeChecking:
				val1Type = self.getBasicSesType(exprCtx.value(0))
			else:
				val1Type = self.getBasicLinType(exprCtx.value(0))
		if isinstance(exprCtx.value(1), PiCalcParser.NamedValueContext):
			val2Type = self.gamma.get(exprCtx.value(1).getText())
		else:
			if self.doSesTypeChecking:
				val2Type = self.getBasicSesType(exprCtx.value(1))
			else:
				val2Type = self.getBasicLinType(exprCtx.value(1))
		if isinstance(val1Type, PiCalcParser.BasicSesTypeContext):
			val1Type = val1Type.basicSType()
		elif isinstance(val1Type, PiCalcParser.BasicLinTypeContext):
			val1Type = val1Type.basicLType()
		if isinstance(val2Type, PiCalcParser.BasicSesTypeContext):
			val2Type = val2Type.basicSType()
		elif isinstance(val2Type, PiCalcParser.BasicLinTypeContext):
			val2Type = val2Type.basicLType()
		return val1Type, val2Type


	def enterEql(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterEqlTCh(ctx)
	def enterEqlTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if not isinstance(val1Type, type(val2Type)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Equal failed due to " + ctx.getText() + ". Equality not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Equal failed due to " + ctx.getText() + ". Equality not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Equal (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Equal (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")
			


	def enterInEql(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterInEqlTCh(ctx)
	def enterInEqlTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if not isinstance(val1Type, type(val2Type)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Inequal failed due to " + ctx.getText() + ". Inequality not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Inequal failed due to " + ctx.getText() + ". Inequality not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Inequal (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Inequal (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntAdd(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntAddTCh(ctx)
	def enterIntAddTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Add failed due to " + ctx.getText() + ". Addition not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Add failed due to " + ctx.getText() + ". Addition not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Add (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Add (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntSub(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntSubTCh(ctx)
	def enterIntSubTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Sub failed due to " + ctx.getText() + ". Subtraction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Sub failed due to " + ctx.getText() + ". Subtraction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Sub (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Sub (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntMult(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntMultTCh(ctx)
	def enterIntMultTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Mult failed due to " + ctx.getText() + ". Multiplication not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Mult failed due to " + ctx.getText() + ". Multiplication not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Mult (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Mult (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntDiv(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntDivTCh(ctx)
	def enterIntDivTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Div failed due to " + ctx.getText() + ". Division not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Div failed due to " + ctx.getText() + ". Division not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Div (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Div (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntMod(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntModTCh(ctx)
	def enterIntModTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Mod failed due to " + ctx.getText() + ". Modulo not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Mod failed due to " + ctx.getText() + ". Modulo not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Mod (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Mod (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntGT(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntGTTCh(ctx)
	def enterIntGTTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Greater failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Greater failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Greater (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Greater (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntGTEq(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntGTEqTCh(ctx)
	def enterIntGTEqTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-GreaterEq failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-GreaterEq failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-GreaterEq (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-GreaterEq (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntLT(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntLTTCh(ctx)
	def enterIntLTTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Less failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Less failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Less (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Less (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterIntLTEq(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterIntLTEqTCh(ctx)
	def enterIntLTEqTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SIntegerContext) or not isinstance(val2Type, PiCalcParser.SIntegerContext)) and (not isinstance(val1Type, PiCalcParser.LIntegerContext) or not isinstance(val2Type, PiCalcParser.LIntegerContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-LessEq failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-LessEq failed due to " + ctx.getText() + ". Ordered comparison not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-LessEq (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-LessEq (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterStrConcat(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterStrConcatTCh(ctx)
	def enterStrConcatTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SStringContext) or not isinstance(val2Type, PiCalcParser.SStringContext)) and (not isinstance(val1Type, PiCalcParser.LStringContext) or not isinstance(val2Type, PiCalcParser.LStringContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Concat failed due to " + ctx.getText() + ". Concatenation not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Concat failed due to " + ctx.getText() + ". Concatenation not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Concat (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Concat (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterBoolNot(self, ctx):
		if self.doSesTypeChecking:
			self.enterBoolNotSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterBoolNotLTCh(ctx)
	def enterBoolNotSTCh(self, ctx):
		if isinstance(ctx.value(), PiCalcParser.NamedValueContext):
			valType = self.gamma.get(ctx.value().getText())
		else:
			valType = self.getBasicSesType(ctx.value())
		if isinstance(valType, PiCalcParser.BasicSesTypeContext):
			valType = valType.basicSType()
		if not isinstance(valType, PiCalcParser.SBooleanContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Not failed due to " + ctx.getText() + ". Logical negation not defined on type " + val1Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Not (◻)", 1)
			self.printVariableTypeRule(ctx.value(), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")
	def enterBoolNotLTCh(self, ctx):
		if isinstance(ctx.value(), PiCalcParser.NamedValueContext):
			valType = self.gamma.get(ctx.value().getText())
		else:
			valType = self.getBasicSesType(ctx.value())
		if isinstance(valType, PiCalcParser.BasicLinTypeContext):
			valType = valType.basicLType()
		if not isinstance(valType, PiCalcParser.LBooleanContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Not failed due to " + ctx.getText() + ". Logical negation not defined on type " + val1Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Not (◻)", 1)
			self.printVariableTypeRule(ctx.value(), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")


	def enterBoolAnd(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterBoolAndTCh(ctx)
	def enterBoolAndTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SBooleanContext) or not isinstance(val2Type, PiCalcParser.SBooleanContext)) and (not isinstance(val1Type, PiCalcParser.LBooleanContext) or not isinstance(val2Type, PiCalcParser.LBooleanContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-And failed due to " + ctx.getText() + ". Logical conjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-And failed due to " + ctx.getText() + ". Logical conjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-And (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-And (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterBoolOr(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterBoolOrTCh(ctx)
	def enterBoolOrTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SBooleanContext) or not isinstance(val2Type, PiCalcParser.SBooleanContext)) and (not isinstance(val1Type, PiCalcParser.LBooleanContext) or not isinstance(val2Type, PiCalcParser.LBooleanContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Or failed due to " + ctx.getText() + ". Logical disjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Or failed due to " + ctx.getText() + ". Logical disjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Or (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Or (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")



	def enterBoolXor(self, ctx):
		if self.doSesTypeChecking or self.doLinTypeChecking:
			self.enterBoolXorTCh(ctx)
	def enterBoolXorTCh(self, ctx):
		val1Type, val2Type = self.getOperandTypes(ctx)
		if (not isinstance(val1Type, PiCalcParser.SBooleanContext) or not isinstance(val2Type, PiCalcParser.SBooleanContext)) and (not isinstance(val1Type, PiCalcParser.LBooleanContext) or not isinstance(val2Type, PiCalcParser.LBooleanContext)):
			if self.doSesTypeChecking:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule T-Xor failed due to " + ctx.getText() + ". Exclusive disjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			else:
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "<span class='error'>ERROR: Typechecking rule Tπ-Xor failed due to " + ctx.getText() + ". Exclusive disjunction not defined on types " + val1Type.getText() + " and " + val2Type.getText() + ".</span>\n"
			raise self.typecheckException
		else:
			if self.doSesTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Xor (◻▵◻)", 1)
			elif self.doLinTypeChecking:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Xor (◻▵◻)", 1)
			self.printVariableTypeRule(ctx.value(0), self.exprGamma)
			self.printVariableTypeRule(ctx.value(1), self.exprGamma)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"☆", u"◻")




	## TYPES
	## Since ▼ represents a placeholder dualed type, if encodedStrBuilder contains a ▼ before a ▲,
	## the next type must be encoded as its dual instead.
	## Due to the properites of the encoding of dual types,
	## This only changes whether the channel is linear input or linear output
	## How the next type, i.e. S in ?T.S or !T.S, is encoded is not affected

	def isNextDual(self):
		firstType = self.encodedStrBuilder.find(u"▲")
		firstDual = self.encodedStrBuilder.find(u"▼")
		return firstDual != -1 and (firstType == -1 or firstDual < firstType)

	def enterTerminate(self, ctx):
		if self.doEncoding:
			self.enterTerminateEnc(ctx)
	# Encode terminate as channel with no capabilities
	def enterTerminateEnc(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", "empty[]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "empty[]", 1)


	def enterReceive(self, ctx):
		if self.doEncoding:
			self.enterReceiveEnc(ctx)
	# Encode a receive as a linear input
	def enterReceiveEnc(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", u"lo[▲, ▲]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", u"li[▲, ▲]", 1)


	def enterSend(self, ctx):
		if self.doEncoding:
			self.enterSendEnc(ctx)
	# Encode a send as a linear output, with the dual of the sType
	def enterSendEnc(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", u"li[▲, ▼]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", u"lo[▲, ▼]", 1)


	def enterBranch(self, ctx):
		if self.doEncoding:
			self.enterBranchEnc(ctx)
	# Encode a branch as a linear input of a variant value
	def enterBranchEnc(self, ctx):
		dual = self.isNextDual()
		self.encStrIndent = self.encStrIndent + "  "
		if dual:
			typeStrBuilder = "lo[<\n" + self.encStrIndent
		else:
			typeStrBuilder = "li[<\n" + self.encStrIndent
		for i in range(len(ctx.opts)):
			typeStrBuilder = typeStrBuilder + ctx.opts[i].getText() + u"_▲"
			if i != (len(ctx.opts) - 1):
				typeStrBuilder = typeStrBuilder + ", \n" + self.encStrIndent
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", typeStrBuilder, 1)

	def exitBranch(self, ctx):
		if self.doEncoding:
			self.exitBranchEnc(ctx)
	def exitBranchEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]


	def enterSelect(self, ctx):
		if self.doEncoding:
			self.enterSelectEnc(ctx)
	# Encode a select as a linear output of a variant value, with the dual of the sTypes
	def enterSelectEnc(self, ctx):
		dual = self.isNextDual()
		self.encStrIndent = self.encStrIndent + "  "
		if dual:
			typeStrBuilder = "li[<\n" + self.encStrIndent
		else:
			typeStrBuilder = "lo[<\n" + self.encStrIndent
		for i in range(len(ctx.opts)):
			typeStrBuilder = typeStrBuilder + ctx.opts[i].getText() + u"_▼"
			if i != (len(ctx.opts) - 1):
				typeStrBuilder = typeStrBuilder + ", \n" + self.encStrIndent
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", typeStrBuilder, 1)

	def exitSelect(self, ctx):
		if self.doEncoding:
			self.exitSelectEnc(ctx)
	def exitSelectEnc(self, ctx):
		self.encStrIndent = self.encStrIndent[:-2]


	# Encode basic types, channel types and type names homomorphically

	def enterNamedTType(self, ctx):
		if self.doEncoding:
			self.enterNamedTTypeEnc(ctx)
	def enterNamedTTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", self.encodeName(ctx.namedType().getText()), 1)

	def enterNamedSType(self, ctx):
		if self.doEncoding:
			self.enterNamedSTypeEnc(ctx)
	def enterNamedSTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", self.encodeName(ctx.namedType().getText()), 1)

	def enterNamedType(self, ctx):
		if self.doEncoding:
			self.enterNamedTypeEnc(ctx)
	def enterNamedTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", self.encodeName(ctx.getText()), 1)

	def enterChannelType(self, ctx):
		if self.doEncoding:
			self.enterChannelTypeEnc(ctx)
	def enterChannelTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", u"#[▲]", 1)

	def enterSUnitType(self, ctx):
		if self.doEncoding:
			self.enterSUnitTypeEnc(ctx)
	def enterSUnitTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "lUnit", 1)

	def enterSBoolean(self, ctx):
		if self.doEncoding:
			self.enterSBooleanEnc(ctx)
	def enterSBooleanEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "lBool", 1)

	def enterSInteger(self, ctx):
		if self.doEncoding:
			self.enterSIntegerEnc(ctx)
	def enterSIntegerEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "lInt", 1)

	def enterSString(self, ctx):
		if self.doEncoding:
			self.enterSStringEnc(ctx)
	def enterSStringEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "lString", 1)


	def enterVariantValue(self, ctx):
		if self.doEncoding:
			self.enterVariantValueEnc(ctx)
	def enterVariantValueEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "<span class='error'>ERROR: Encoding failed. Variant values not supported in session-typed pi calculus.</span>\n"
		raise self.encodingException