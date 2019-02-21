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
		## THESE VARIABLES ARE USED FOR TYPECHECKING
		## typeCheckStrBuilder is used to display that the typechecking was succesful, and what typechecking rules were applied.
		##   ◻ is used as a placeholder for the rules, ▵ is used as a placeholder for commas.
		## tcErrorStrBuilder is used to display any errors that occur while typechecking, i.e. why typechecking has failed.
		## gamma is the current type context
		## gammaStack is a stack of type contexts to be used
		##   Whenever typechecking a process requires typechecking the continuation process,
		##   the gamma to be used to typecheck that process is pushed onto the stack
		##   The listener then traverses to the continuation process, and pops the required gamma off the stack
		##   Composition pushes two different gammas, branch pushes multiple copies of the same gamma
		##   gammaStack has an empty gamma by default, in case there are no type declarations given
		##   This default is discarded if declarations are present
		## typeNames is a dictionary containing any types which have been given names
		##   i.e. if there is a statement 'type foo := ?Int.end', typeNames['foo'] contains a context representing ?Int.end
		##   this is used when initially adding types to gamma, that is, gamma uses the full type, not the name
		self.typeCheckStrBuilder = u"Typechecking successful. Rules used: \n◻"
		self.tcStrIndent = ""
		self.tcErrorStrBuilder = ""
		self.gamma = {}
		self.gammaStack = [{}]
		self.typeNames = {}
		## THESE VARIABLES ARE USED FOR THE ENCODING
		## encodedStrBuilder is used to reconstruct the pi calc string.
		## warnStrBuilder is used to construct warning messages
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
		## delayedProcesses stores the ANTLR contexts for named processes so they can be handled later
		##   When a process P is named, the processing of P should not be performed until P appears in the user-input process.
		##   So the ANTLR context for the process is stored until later.
		##   The ANTLR context of the type in the type annotation is also stored.
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
		self.warnStrBuilder = ""
		self.encErrorStrBuilder = ""
		self.encFunc = {}
		self.contChanTypes = {}
		self.contChanTypesStack = []
		self.delayedProcesses = {}
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
			if isinstance(v, PiCalcParser.SessionTypeContext) and self.sesLinType(v.sType()):
				return True
		return False

	# Given an ANTLR context of a session type, produce a context of the dual type
	def getSesTypeDual(self, typeCtx):
		typeStr = typeCtx.getText()
		dualStr = typeStr.translate(dict(zip([ord(char) for char in u"?!&+"], [ord(char) for char in u"!?+&"])))
		lex_inp = InputStream(dualStr)
		lex = PiCalcLexer(lex_inp)
		stream = CommonTokenStream(lex)
		par = PiCalcParser(stream)
		return par.sType()

	# Given an ANTLR context of a literal value, return the context of that literal's type
	def getBasicSesType(self, literalValue):
		lex_inp = InputStream("")
		if isinstance(literalValue, PiCalcParser.IntegerValueContext):
			lex_inp = InputStream("sInt")
		elif isinstance(literalValue, PiCalcParser.StringValueContext):
			lex_inp = InputStream("sString")
		elif isinstance(literalValue, PiCalcParser.BooleanValueContext):
			lex_inp = InputStream("sBool")
		lex = PiCalcLexer(lex_inp)
		stream = CommonTokenStream(lex)
		par = PiCalcParser(stream)
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
				if varName in capabilities:
					if isinstance(varType, PiCalcParser.LinearConnectionContext):
						(varTypeIn, varTypeOut) = self.splitCapabilities(varType)
						if capabilities[varName] == "Input":
							gamma1[varName] = varTypeIn
							gamma2[varName] = varTypeOut
						elif capabilities[varName] == "Output":
							gamma1[varName] = varTypeOut
							gamma2[varName] = varTypeIn
						else:
							gamma1[varName] = varType
					else:
						gamma1[varName] = varType
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
		### IMPLEMENT VARIANT

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
		lex_inpIn = InputStream(linInStr)
		lexIn = PiCalcLexer(lex_inpIn)
		streamIn = CommonTokenStream(lexIn)
		parIn = PiCalcParser(streamIn)
		lex_inpOut = InputStream(linOutStr)
		lexOut = PiCalcLexer(lex_inpOut)
		streamOut = CommonTokenStream(lexOut)
		parOut = PiCalcParser(streamOut)
		return (parIn.linearType(), parOut.linearType())

	# Given an ANTLR context of a literal value, return the context of that literal's type
	def getBasicLinType(self, literalValue):
		lex_inp = InputStream("")
		if isinstance(literalValue, PiCalcParser.IntegerValueContext):
			lex_inp = InputStream("lInt")
		elif isinstance(literalValue, PiCalcParser.StringValueContext):
			lex_inp = InputStream("lString")
		elif isinstance(literalValue, PiCalcParser.BooleanValueContext):
			lex_inp = InputStream("lBool")
		lex = PiCalcLexer(lex_inp)
		stream = CommonTokenStream(lex)
		par = PiCalcParser(stream)
		return par.basicLType()

	# Given an ANTLR context of a linear type, produce a context of the dual type
	def getLinTypeDual(self, typeCtx):
		typeStr = typeCtx.getText()
		dualStr = typeStr[:2].translate(dict(zip([ord(char) for char in "io"], [ord(char) for char in "oi"]))) + typeStr[2:]
		lex_inp = InputStream(dualStr)
		lex = PiCalcLexer(lex_inp)
		stream = CommonTokenStream(lex)
		par = PiCalcParser(stream)
		return par.linearType()


	def getTypeCheckResults(self):
		if self.tcErrorStrBuilder != "" or self.encErrorStrBuilder != "":
			self.typeCheckStrBuilder = ""
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"▵", ", ")
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace("\n\n", "\n")
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
		#oldStr = self.encodedStrBuilder
		#self.encodedStrBuilder = self.encodedStrBuilder.translate({ord(c): None for c in u"◼▲▼●⬥⬟"})
		#if self.encErrorStrBuilder == "" and self.tcErrorStrBuilder == "":
		#	if (oldStr != self.encodedStrBuilder):
		#		self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: The pi calculus could not be encoded. Please check that your input is valid.\n"
		#if self.encErrorStrBuilder != "" or self.tcErrorStrBuilder != "":
		#	self.encodedStrBuilder = ""
		return (self.encodedStrBuilder, self.warnStrBuilder, self.encErrorStrBuilder)


	## LISTENER METHODS

	## Encoding explanation:
	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## ◼ represents placeholder type declarations,
	## ▲ represents placeholder type, ▼ represents a placeholder type's dual,
	## ● represents placeholder processes, ⬥ represents placeholder values,
	## ⬟ represents placeholder process name declarations


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
	# No type, so no change needed
	def enterVariableAssignmentEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", ctx.getText(), 1)


	def enterProcessNamingNmd(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingNmdEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(self.typeNames[ctx.typeName.text]), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()
	# Save context for process naming for later
	def enterProcessNamingNmdEnc(self, ctx):
		fullType = self.typeNames.get(ctx.typeName.text)
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: Process naming containing linear types are not supported in session pi calculus.\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.value().getText()] = fullType.sType()
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", u"⬟", 1)


	def enterProcessNamingSes(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingSesEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.tType()), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()
	# Save context for process naming for later
	def enterProcessNamingSesEnc(self, ctx):
		self.contChanTypes[ctx.value().getText()] = ctx.tType().sType()
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", u"⬟", 1)


	def exitProcessNamingSes(self, ctx):
		if self.doEncoding:
			self.exitProcessNamingSesEnc(ctx)
	def exitProcessNamingSesEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterProcessNamingLin(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingLinEnc(ctx)
		self.delayedProcesses[ctx.name.text] = (copy.deepcopy(ctx.value()), copy.deepcopy(ctx.linearType()), copy.deepcopy(ctx.processPrim()))
		for i in range(ctx.getChildCount()):
			ctx.removeLastChild()
	# Raise error if linear version of process naming is used in encoding
	def enterProcessNamingLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: Process naming containing linear types are not supported in session pi calculus.\n"
		raise self.encodingException


	def enterSessionTypeNaming(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionTypeNamingSTCh(ctx)
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

	def exitSessionTypeNaming(self, ctx):
		if self.doEncoding:
			self.exitSessionTypeNamingEnc(ctx)
	def exitSessionTypeNamingEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterBasicTypeDecl(self, ctx):
		if self.doSesTypeChecking:
			self.enterBasicTypeDeclSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterBasicTypeDeclLTCh(ctx)
		if self.doEncoding:
			self.enterBasicTypeDeclEnc(ctx)
	# Place type placeholder
	def enterBasicTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterBasicTypeDeclSTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.basicType()
	def enterBasicTypeDeclLTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.basicType()


	def enterBasTypeDeclAndAssign(self, ctx):
		if self.doSesTypeChecking:
			self.enterBasTypeDeclAndAssignSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterBasTypeDeclAndAssignLTCh(ctx)
		if self.doEncoding:
			self.enterBasTypeDeclAndAssignEnc(ctx)
	# Place type placeholder
	def enterBasTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterBasTypeDeclAndAssignSTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.basicType()
	def enterBasTypeDeclAndAssignLTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.basicType()


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
		fullType = self.typeNames.get(ctx.typeName.text)
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Type declaration contains undeclared type name.\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType
	def enterNamedTypeDeclLTCh(self, ctx):
		fullType = self.typeNames.get(ctx.typeName.text)
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Type declaration contains undeclared type name.\n"
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
		fullType = self.typeNames.get(ctx.typeName.text)
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Type declaration contains undeclared type name.\n"
			raise self.typecheckException
		self.gamma[ctx.var.text] = fullType
	def enterNmdTypeDeclAndAssignLTCh(self, ctx):
		fullType = self.typeNames.get(ctx.typeName.text)
		if fullType == None:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Type declaration contains undeclared type name.\n"
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
		self.gamma[ctx.var.text] = ctx.tType()


	def enterSesTypeDeclAndAssign(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionTypeDeclSTCh(ctx)
		if self.doEncoding:
			self.enterSesTypeDeclAndAssignEnc(ctx)
	# Place type placeholder
	def enterSesTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.var.text] = ctx.tType()
	def enterSesTypeDeclAndAssignSTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.tType()


	def enterLinearTypeNaming(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinearTypeNamingLTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeNamingEnc(ctx)
	# Leave type declarations as is and display warning.
	def enterLinearTypeNamingEnc(self, ctx):
		decStr = "type " + ctx.name.text + " := " + ctx.linearType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinearTypeNamingLTCh(self, ctx):
		self.typeNames[ctx.name.text] = ctx.linearType()


	def enterLinearTypeDecl(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinearTypeDeclLTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeDeclEnc(ctx)
	# Leave linear type declarations as is and display warning.
	def enterLinearTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinearTypeDeclLTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.linearType()


	def enterLinTypeDeclAndAssign(self, ctx):
		if self.doLinTypeChecking:
			self.enterLinTypeDeclAndAssignLTCh(ctx)
		if self.doEncoding:
			self.enterLinTypeDeclAndAssignEnc(ctx)
	# Leave linear type declarations as is and display warning.
	def enterLinTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType.getText() + " = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinTypeDeclAndAssignLTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.linearType()



	def enterTermination(self, ctx):
		if self.doSesTypeChecking:
			self.enterTerminationSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterTerminationLTCh(ctx)
		if self.doEncoding:
			self.enterTerminationEnc(ctx)
	# Termination encoded homomorphically
	def enterTerminationEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "0", 1)
	def enterTerminationSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if self.sesLinGamma(self.gamma):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Termination occurs while context is still linear.\n"
			raise self.typecheckException
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Inact", 1)
	def enterTerminationLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if self.linLinGamma(self.gamma):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Termination occurs while context is still linear.\n"
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
		if isinstance(delayType, PiCalcParser.NamedSTypeContext) or isinstance(delayType, PiCalcParser.NamedTTypeContext):
			delayType = self.typeNames[delayType.getText()]
		if isinstance(delayType, PiCalcParser.SessionTypeContext):
			delayType = delayType.sType()
		if not isinstance(delayType, type(self.gamma.get(ctx.value().getText()))):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value.getText() + ". Channel type used in named process does not match named process declaration.\n"
			raise self.typecheckException
		else:
			self.gamma[delayChan.getText()] = self.gamma[ctx.value().getText()]
			self.gammaStack.append(self.gamma)
	def enterNamedProcessLTCh(self, ctx, delayChan, delayType, delayProc):
		self.gamma = self.gammaStack.pop()
		if isinstance(delayType, PiCalcParser.NamedLinTypeContext):
			delayType = self.typeNames[delayType.getText()]
		if not isinstance(delayType, type(self.gamma.get(ctx.value().getText()))):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Channel type used in named process does not match named process declaration.\n"
			raise self.typecheckException
		else:
			self.gamma[delayChan.getText()] = self.gamma[ctx.value().getText()]
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
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "send(" + ctx.channel.getText() + ", " + ctx.payload[0].getText() + u").●", 1)
		else:
			newChan = self.generateChannelName()
			newChanType = self.contChanTypes[ctx.channel.getText()].sType()
			self.contChanTypes[ctx.channel.getText()] = newChanType
			opStrBuilder = "(new " + newChan + u" : ▲) (send(" + self.encodeName(ctx.channel.getText())
			if (len(ctx.payload)) > 1:
				self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: send() cannot have multiple payloads in session pi calculus.\n"
				raise self.encodingException
			opStrBuilder = opStrBuilder + ", " + self.encodeName(ctx.payload[0].getText()) + ", " + newChan + u").●)"
			self.encFunc[ctx.channel.getText()] = newChan
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", opStrBuilder, 1)
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType)
	def enterOutputSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2_3) = self.splitGamma(self.gamma, [ctx.channel.getText()])
		if (len(ctx.payload)) > 1:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: send() cannot have multiple payloads in session pi calculus.\n"
			raise self.typecheckException
		(gamma2, gamma3) = self.splitGamma(gamma2_3, [ctx.payload[0].getText()])
		chanType = gamma1.get(ctx.channel.getText())
		if isinstance(ctx.payload[0], PiCalcParser.NamedValueContext):
			payloadType = gamma2.get(ctx.payload[0].getText())
		## Handle literals
		else:
			payloadType = self.getBasicSesType(ctx.payload[0])
		if isinstance(payloadType, PiCalcParser.BasicSesTypeContext):
			payloadType = payloadType.basicSType()
		if not isinstance(chanType, PiCalcParser.ChannelTypeContext):
			if not isinstance(chanType, PiCalcParser.SendContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Output process on channel not of output type.\n"
				raise self.typecheckException
			elif not isinstance(payloadType, type(chanType.tType().basicSType()) if isinstance(chanType.tType(), PiCalcParser.BasicSesTypeContext) else type(chanType.tType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.payload[0].getText() + ". Output process payload does not match channel type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
				augmentations = {ctx.channel.getText(): chanType.sType()}
				gamma3 = self.augmentGamma(gamma3, augmentations)
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Out▵◻", 1)
		else:
			if not isinstance(payloadType, type(chanType.tType().basicSType()) if isinstance(chanType.tType(), PiCalcParser.BasicSesTypeContext) else type(chanType.tType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.payload[0].getText() + ". Output process payload does not match channel type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
				augmentations = {ctx.channel.getText(): chanType}
				gamma3 = self.augmentGamma(gamma3, augmentations)
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndOut▵◻", 1)
	def enterOutputLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2_3) = self.combineGamma(self.gamma, [(ctx.channel.getText(), "Output")])
		plCaps = []
		for pl in ctx.payload:
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
		chanType = gamma1.get(ctx.channel.getText())
		payloadTypes = [[] for i in range(len(ctx.payload))]
		for i in range(len(ctx.payload)):
			if isinstance(ctx.payload[i], PiCalcParser.NamedValueContext) or isinstance(ctx.payload[i], PiCalcParser.VariantValueContext):
				payloadTypes[i] = gamma2.get(ctx.payload[i].getText())
			## Handle literals
			else:
				payloadTypes[i] = self.getBasicLinType(ctx.payload[i])
			if isinstance(payloadTypes[i], PiCalcParser.BasicLinTypeContext):
				payloadTypes[i] = payloadTypes[i].basicLType()
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearOutputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Output process on channel not of output type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
				for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payload[i].basicLType()) if isinstance(chanType.payload[i], PiCalcParser.BasicLinTypeContext) else type(chanType.payload[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "EEROR: Typechecking failed due to " + ctx.payload[i].getText() + ". Output process payload does not match channel type.\n"
						raise self.typecheckException
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Out▵◻", 1)
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
			for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payload[i].basicLType()) if isinstance(chanType.payload[i], PiCalcParser.BasicLinTypeContext) else type(chanType.payload[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "EEROR: Typechecking failed due to " + ctx.payload[i].getText() + ". Output process payload does not match channel type.\n"
						raise self.typecheckException
			augmentations = {ctx.channel.getText(): chanType}
			gamma3 = self.augmentGamma(gamma3, augmentations)
			self.gammaStack.append(gamma3)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-StndOut▵◻", 1)


	# Output of variants, such as encoding of select, uses separate rule to allow for type annotations
	def enterOutputVariants(self, ctx):
		if self.doLinTypeChecking:
			self.enterOutputVariantsLTCh(ctx)
	def enterOutputVariantsLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2_3) = self.combineGamma(self.gamma, [(ctx.channel.getText(), "Output")])
		plCaps = []
		for pl in ctx.payload:
			plCaps.append((pl.getText(), ""))
			if (pl.getText() + u"▼").split("_")[1] in gamma2_3:
				plCaps.append(((pl.getText() + u"▼").split("_")[1], ""))
		(gamma2, gamma3) = self.combineGamma(gamma2_3, plCaps)
		chanType = gamma1.get(ctx.channel.getText())
		payloadTypes = [[] for i in range(len(ctx.payload))]
		for i in range(len(ctx.payload)):
			payloadTypes[i] = ctx.plType[i]
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearOutputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Output process on channel not of output type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
				for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payload[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "EEROR: Typechecking failed due to " + ctx.payload[i].getText() + ". Output process payload does not match channel type.\n"
						raise self.typecheckException
				self.gammaStack.append(gamma3)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Out▵◻", 1)
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
			for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payload[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "EEROR: Typechecking failed due to " + ctx.payload[i].getText() + ". Output process payload does not match channel type.\n"
						raise self.typecheckException
			augmentations = {ctx.channel.getText(): chanType}
			gamma3 = self.augmentGamma(gamma3, augmentations)
			self.gammaStack.append(gamma3)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-StndOut▵◻", 1)


	def exitOutput(self, ctx):
		if self.doEncoding:
			self.exitOutputEnc(ctx)
	def exitOutputEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterInputSes(self, ctx):
		if self.doSesTypeChecking:
			self.enterInputSesSTCh(ctx)
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
			ipStrBuilder = ipStrBuilder + ", " + newChan + u" : ▲).●"
			self.encFunc[ctx.channel.getText()] = newChan
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", ipStrBuilder, 1)
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType)
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"★", u"▲", 1)
	def enterInputSesSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2) = self.splitGamma(self.gamma, [ctx.channel.getText()])
		chanType = gamma1.get(ctx.channel.getText())
		payloadType = ctx.tType()
		if isinstance(payloadType, PiCalcParser.BasicSesTypeContext):
			payloadType = payloadType.basicSType()
		if not isinstance(chanType, PiCalcParser.ChannelTypeContext):
			if not isinstance(chanType, PiCalcParser.ReceiveContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder = "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Input process on channel not of receive type.\n"
				raise self.typecheckException
			elif not isinstance(payloadType, type(chanType.tType().basicSType()) if isinstance(chanType.tType(), PiCalcParser.BasicSesTypeContext) else type(chanType.tType())):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder = "ERROR: Typechecking failed due to " + ctx.payload.getText() + ". Input process payload has type annotation that does not match channel type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
				augmentations = {ctx.channel.getText(): chanType.sType(), ctx.payload.getText(): chanType.tType()}
				gamma2 = self.augmentGamma(gamma2, augmentations)
				self.gammaStack.append(gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-In▵◻", 1)
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
			augmentations = {ctx.channel.getText(): chanType, ctx.payload.getText(): chanType.tType()}
			gamma2 = self.augmentGamma(gamma2, augmentations)
			self.gammaStack.append(gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndIn▵◻", 1)

	def exitInputSes(self, ctx):
		if self.doEncoding:
			self.exitInputSesEnc(ctx)
	def exitInputSesEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterInputLin(self, ctx):
		if self.doLinTypeChecking:
			self.enterInputLinLTCh(ctx)
		if self.doEncoding:
			self.enterInputLinEnc(ctx)
	# Raise error if linear version of input is used in encoding
	def enterInputLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: Receive statements containing linear types and/or multiple payloads are not supported in session pi calculus.\n"
		raise self.encodingException
	def enterInputLinLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2) = self.combineGamma(self.gamma, [(ctx.channel.getText(), "Input")])
		chanType = gamma1.get(ctx.channel.getText())
		payloadTypes = copy.deepcopy(ctx.plType)
		for i in range(len(payloadTypes)):
			if isinstance(payloadTypes[i], PiCalcParser.BasicLinTypeContext):
				payloadTypes[i] = payloadTypes[i].basicLType()
		if not isinstance(chanType, PiCalcParser.ConnectionContext):
			if not isinstance(chanType, PiCalcParser.LinearInputContext):
				self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Input process on channel not of input type.\n"
				raise self.typecheckException
			else:
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
				augmentations = {}
				for i in range(len(payloadTypes)):
					if not isinstance(payloadTypes[i], type(chanType.payload[i].basicLType()) if isinstance(chanType.payload[i], PiCalcParser.BasicLinTypeContext) else type(chanType.payload[i])):
						self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.payload[i].getText() + ". Input process payload has type annotation that does not match channel type.\n"
						raise self.typecheckException
					augmentations[ctx.payload[i].getText()] = chanType.payload[i]
				gamma2 = self.augmentGamma(gamma2, augmentations)
				self.gammaStack.append(gamma2)
				self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Inp▵◻", 1)
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
			augmentations = {ctx.channel.getText(): chanType}
			for i in range(len(payloadTypes)):
				augmentations[ctx.payload[i].getText()] = chanType.payload[i]
			gamma2 = self.augmentGamma(gamma2, augmentations)
			self.gammaStack.append(gamma2)
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-StndInp▵◻", 1)



	def enterSelection(self, ctx):
		if self.doSesTypeChecking:
			self.enterSelectionSTCh(ctx)
		if self.doEncoding:
			self.enterSelectionEnc(ctx)
	# Create new channel and send as variant value
	# ★ used so type annotations appear in correct order
	def enterSelectionEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		newChan = self.generateChannelName()
		newChanType = self.contChanTypes[ctx.channel.getText()]
		selStrBuilder = "(new " + newChan + u" : ★) (send(" + self.encodeName(ctx.channel.getText()) + "," + ctx.selection.getText() + "_" + newChan + " : <\n"
		for i in range(len(newChanType.option)):
			selStrBuilder = selStrBuilder + "    " + newChanType.option[i].getText() +  u"_▲"
			if i != len(newChanType.option)-1:
				selStrBuilder = selStrBuilder + ", \n"
		selStrBuilder = selStrBuilder + u">).\n    ●)"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", selStrBuilder, 1)
		for i in range(len(newChanType.cont)):
			typeWalker = ParseTreeWalker()
			typeWalker.walk(self, newChanType.cont[i])
			if newChanType.option[i].getText() == ctx.selection.getText():
				self.encodedStrBuilder = self.encodedStrBuilder.replace(u"★", u"▲", 1)
				self.contChanTypes[ctx.channel.getText()] = newChanType.cont[i]
				typeWalker.walk(self, newChanType.cont[i])
	def enterSelectionSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2) = self.splitGamma(self.gamma, [ctx.channel.getText()])
		chanType = gamma1.get(ctx.channel.getText())
		if not isinstance(chanType, PiCalcParser.SelectContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Select process on channel not of select type.\n"
			raise self.typecheckException
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
			for i in range(len(chanType.option)):
				if chanType.option[i].getText() == ctx.selection.getText():
					selType = chanType.cont[i]
			gamma2 = self.augmentGamma(gamma2, {ctx.channel.getText(): selType})
			self.gammaStack.append(gamma2)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Sel▵◻", 1)

	def exitSelection(self, ctx):
		if self.doEncoding:
			self.exitSelectionEnc(ctx)
	def exitSelectionEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterBranching(self, ctx):
		if self.doSesTypeChecking:
			self.enterBranchingSTCh(ctx)
		if self.doEncoding:
			self.enterBranchingEnc(ctx)
	# Receive value then use for case statement
	def enterBranchingEnc(self, ctx):
		self.checkBranchStack(True)
		self.checkCompStack(False)
		caseVar = self.generateChannelName()
		caseVarType = self.contChanTypes[ctx.channel.getText()]
		for i in range(len(caseVarType.cont)-1, -1, -1):
			cctCopy = copy.deepcopy(self.contChanTypes)
			cctCopy[ctx.channel.getText()] = caseVarType.cont[i]
			self.contChanTypesStack.append(cctCopy)
		brnStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + "," + caseVar + " : <\n"
		for i in range(len(caseVarType.option)):
			brnStrBuilder = brnStrBuilder + "    " + caseVarType.option[i].getText() + u"_▲"
			if i != len(caseVarType.option)-1:
				brnStrBuilder = brnStrBuilder + ", \n"
		brnStrBuilder = brnStrBuilder + ">).\n    case " + caseVar + " of { \n"
		newChan = self.generateChannelName()
		for i in range(len(ctx.option)):
			brnStrBuilder = brnStrBuilder + "    " + ctx.option[i].getText() + "_(" + newChan + u" : ▲)" + " > " + u"\n        ●"
			if i != (len(ctx.option) - 1):
				brnStrBuilder = brnStrBuilder + ", \n"
			else:
				brnStrBuilder = brnStrBuilder + " }"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encFuncBackupStack.append(copy.deepcopy(self.encFunc))
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		self.branchStack.append("B")
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", brnStrBuilder, 1)
		for i in range(2):
			for i in range(len(caseVarType.cont)):
				typeWalker = ParseTreeWalker()
				typeWalker.walk(self, caseVarType.cont[i])
	def enterBranchingSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2) = self.splitGamma(self.gamma, [ctx.channel.getText()])
		chanType = gamma1.get(ctx.channel.getText())
		if not isinstance(chanType, PiCalcParser.BranchContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.channel.getText() + ". Branch process on channel not of branch type.\n"
			raise self.typecheckException
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-Var▵◻", 1)
			for i in range(len(chanType.cont)-1, -1, -1):
				brchGamma = self.augmentGamma(gamma2, {ctx.channel.getText(): chanType.cont[i]})
				self.gammaStack.append(brchGamma)
		self.tcStrIndent = self.tcStrIndent + "  "
		brchTcStrBuilder = u"T-Brch\n" + self.tcStrIndent + "{"
		for i in range(len(ctx.option)):
			brchTcStrBuilder = brchTcStrBuilder + ctx.option[i].getText() + u" : ◻"
			if i != (len(ctx.option) -1):
				brchTcStrBuilder = brchTcStrBuilder + ";\n" + self.tcStrIndent
			else:
				self.tcStrIndent = self.tcStrIndent[:-2]
				brchTcStrBuilder = brchTcStrBuilder + "}\n" + self.tcStrIndent
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", brchTcStrBuilder, 1)

	def exitBranching(self, ctx):
		if self.doEncoding:
			self.exitBranchingEnc(ctx)
	def exitBranchingEnc(self, ctx):
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
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"(● | ●)", 1)
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
		if self.compStack != []:
			self.compStack.pop()
		if self.varNamesBackupStack != []:
			self.varNamesBackupStack.pop()


	def enterSessionRestriction(self, ctx):
		if self.doSesTypeChecking:
			self.enterSessionRestrictionSTCh(ctx)
		if self.doEncoding:
			self.enterSessionRestrictionEnc(ctx)
	# Create new channel to replace both endpoints
	def enterSessionRestrictionEnc(self, ctx):
		newChan = self.generateChannelName()
		for ep in ctx.endpoint:
			self.encFunc[ep.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "(new " + newChan + u" : ▲) (●)", 1)
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
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.endpoint[0].getText() + " or " + ctx.endpoint[1].getText() + ". Attempting to restrict variable name already in use.\n"
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


	def enterChannelRestrictionNmd(self, ctx):
		if self.doSesTypeChecking:
			self.enterChannelRestrictionNmdSTCh(ctx)
		if self.doLinTypeChecking:
			self.enterChannelRestrictionNmdLTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionNmdEnc(ctx)
	# Channel Restriction encoded homomorphically
	def enterChannelRestrictionNmdEnc(self, ctx):
		fullType = self.typeNames.get(ctx.typeName.text)
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: Channel restrictions containing linear types are not supported in session pi calculus.\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.contChanTypes[ctx.value().getText()] = fullType			
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"(new ⬥ : ▲) (●)", 1)
	def enterChannelRestrictionNmdSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.\n"
			raise self.typecheckException
		fullType = self.typeNames.get(ctx.typeName.text)
		if isinstance(fullType, PiCalcParser.LinearTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Channel restrictions containing linear types are not supported in session pi calculus.\n"
			raise self.encodingException
		elif isinstance(fullType, PiCalcParser.SessionTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Channel restriction on a session type.\n"
			raise self.typecheckException
		newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : fullType})
		self.gammaStack.append(newGamma)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + fullType.getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)
	def enterChannelRestrictionNmdLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.\n"
			raise self.typecheckException
		fullType = self.typeNames.get(ctx.typeName.text)
		if isinstance(fullType, PiCalcParser.TTypeContext) or isinstance(fullType, PiCalcParser.STypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Channel restrictions containing session types are not supported in linear pi calculus.\n"
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


	def enterChannelRestrictionSes(self, ctx):
		if self.doSesTypeChecking:
			self.enterChannelRestrictionSesSTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionSesEnc(ctx)
	# Channel Restriction encoded homomorphically
	def enterChannelRestrictionSesEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"(new " + ctx.value().getText() + u" : ▲) (●)", 1)
		self.contChanTypes[ctx.value().getText()] = ctx.tType()
	def enterChannelRestrictionSesSTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.\n"
			raise self.typecheckException
		if isinstance(ctx.tType(), PiCalcParser.SessionTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Channel restriction on a session type.\n"
			raise self.typecheckException
		newGamma = self.augmentGamma(self.gamma, {ctx.value().getText() : ctx.tType()})
		self.gammaStack.append(newGamma)
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"T-StndRes \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.tType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)


	def enterChannelRestrictionLin(self, ctx):
		if self.doLinTypeChecking:
			self.enterChannelRestrictionLinLTCh(ctx)
		if self.doEncoding:
			self.enterChannelRestrictionLinEnc(ctx)
	# Raise error if linear version of channel restriction is used in encoding
	def enterChannelRestrictionLinEnc(self, ctx):
		self.encErrorStrBuilder = self.encErrorStrBuilder + "ERROR: Channel restrictions containing linear types are not supported in session pi calculus.\n"
		raise self.encodingException
	def enterChannelRestrictionLinLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		if ctx.value().getText() in self.gamma:
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.value().getText() + ". Attempting to restrict variable name already in use.\n"
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
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Res1 \n" + self.tcStrIndent + "[" + ctx.value().getText() + " : " + ctx.linearType().getText().replace(",", ", ") + u"]▵\n" + self.tcStrIndent + u"◻", 1)


	def enterCase(self, ctx):
		if self.doLinTypeChecking:
			self.enterCaseLTCh(ctx)
		if self.doEncoding:
			self.enterCaseEnc(ctx)
	# Case is not native to session pi calculus, so encode homomorphically and display warning
	def enterCaseEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"case ⬥ of {⬥ > ●, ⬥ > ●}", 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Case statements are not native to session pi calculus.\n"
	def enterCaseLTCh(self, ctx):
		self.gamma = self.gammaStack.pop()
		(gamma1, gamma2) = self.combineGamma(self.gamma, [(ctx.case.getText(), "")])
		caseType = gamma1.get(ctx.case.getText())
		if not isinstance(caseType, PiCalcParser.VariantTypeContext):
			self.tcErrorStrBuilder = self.tcErrorStrBuilder + "ERROR: Typechecking failed due to " + ctx.case.getText() + ". Case statement with case variable not of variant type.\n"
			raise self.typecheckException
		else:
			self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", u"Tπ-Var▵◻", 1)
			for i in range(len(caseType.cont)-1, -1, -1):
				caseGamma = self.augmentGamma(gamma2, {ctx.option[i].value().getText(): caseType.cont[i]})
				self.gammaStack.append(caseGamma)
		self.tcStrIndent = self.tcStrIndent + "  "
		caseTcStrBuilder = u"Tπ-Case\n" + self.tcStrIndent + "{"
		for i in range(len(ctx.option)):
			caseTcStrBuilder = caseTcStrBuilder + ctx.option[i].ID().getText() + u" : ◻"
			if i != (len(ctx.option) -1):
				caseTcStrBuilder = caseTcStrBuilder + ";\n" + self.tcStrIndent
			else:
				caseTcStrBuilder = caseTcStrBuilder + "}\n" + self.tcStrIndent[:-2]
		self.typeCheckStrBuilder = self.typeCheckStrBuilder.replace(u"◻", caseTcStrBuilder, 1)



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
		if dual:
			typeStrBuilder = "lo[<"
		else:
			typeStrBuilder = "li[<"
		for i in range(len(ctx.option)):
			typeStrBuilder = typeStrBuilder + ctx.option[i].getText() + u"_▲"
			if i != (len(ctx.option) - 1):
				typeStrBuilder = typeStrBuilder + ", \n    "
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", typeStrBuilder, 1)


	def enterSelect(self, ctx):
		if self.doEncoding:
			self.enterSelectEnc(ctx)
	# Encode a select as a linear output of a variant value, with the dual of the sTypes
	def enterSelectEnc(self, ctx):
		dual = self.isNextDual()
		if dual:
			typeStrBuilder = "li[<"
		else:
			typeStrBuilder = "lo[<"
		for i in range(len(ctx.option)):
			typeStrBuilder = typeStrBuilder + ctx.option[i].getText() + u"_▼"
			if i != (len(ctx.option) - 1):
				typeStrBuilder = typeStrBuilder + ", \n    "
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▼", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", typeStrBuilder, 1)


	# Encode basic types, channel types and type names homomorphically

	def enterNamedTType(self, ctx):
		if self.doEncoding:
			self.enterNamedTTypeEnc(ctx)
	def enterNamedTTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", self.encodeName(ctx.name.text), 1)

	def enterNamedSType(self, ctx):
		if self.doEncoding:
			self.enterNamedSTypeEnc(ctx)
	def enterNamedSTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", self.encodeName(ctx.name.text), 1)

	# def enterNamedLinTypeEnc(self, ctx):
	# 	self.encodedStrBuilder = self.encodedStrBuilder.replace("▲", ctx.name.text)

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


	def enterUnitValue(self, ctx):
		if self.doEncoding:
			self.enterUnitValueEnc(ctx)
	# Unit value encoded homomorphically
	def enterUnitValueEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"⬥", "*", 1)


	def enterName(self, ctx):
		if self.doEncoding:
			self.enterNameEnc(ctx)
	# In theory, may be unneeded?
	def enterNameEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"⬥", ctx.getText(), 1)


	def enterVariantValue(self, ctx):
		if self.doEncoding:
			self.enterVariantValueEnc(ctx)
	# In theory, may be unneeded? Variant value also not native to session pi calculus
	def enterVariantValueEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"⬥", u"l_⬥", 1)