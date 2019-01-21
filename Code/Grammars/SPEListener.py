# encoding: utf-8
from antlr4 import *
from PiCalcListener import PiCalcListener
from PiCalcParser import PiCalcParser
import copy

class SPEListener(PiCalcListener):

	def __init__(self, typecheck, encode ,varNameList):
		## THESE VARIABLES ARE USED TO DECIDE WHAT OPERATIONS TO PERFORM
		self.doTypeChecking = typecheck
		self.doEncoding = encode
		## THESE VARIABLES ARE USED FOR TYPECHECKING
		## gamma is the current type context
		## gammaStack is a stack of type contexts to be used
		##   Whenever typechcking a process requires typechecking the continuation process,
		##   the gamma to be used to typecheck that process is pushed onto the stack
		##   The listener then traverses to the continuation process, and pops the required gamma off the stack
		##   Composition pushes two different gammas, branch pushes multiple copies of the same gamma
		## typeNames is a dictionary containing any types which have been given names
		##   i.e. if there is a statement 'type foo := ?Int.end', typeNames['foo'] = '?Int.end'
		##   this is used when initially adding types to gamma, that is, gamma uses the full type, not the name
		self.gamma = {}
		self.gammaStack = []
		self.typeNames = {}
		## THESE VARIABLES ARE USED FOR THE ENCODING
		## encodedStrBuilder is used to reconstruct the pi calc string.
		## warnStrBuilder is used to construct warning messages
		## errorStrBuilder is used to construct error messages
		## encFunc is the encoding function f that renames variables in the encoding
		## i.e. replaces subsequent instances of session endpoint x with linear channel c
		## usedVarNames is a list of user-made variable names,
		## collected by VariableNameCollector.py, used to prevent the encoding 
		## from generating variables names that already exist in the code
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
		self.warnStrBuilder = ""
		self.errorStrBuilder = ""
		self.encFunc = {}
		self.usedVarNames = varNameList
		self.branchStack = []
		self.encFuncBackupStack = []
		self.varNamesBackupStack = []
		self.compStack = []


	## Supplementary functions for typechecking

	# Augment a context with additional name-type pairs without changing original context
	# i.e. return resulting context of G, x:T1, y:T2
	# gamma and aug should both be dictionaries, 
	# gamma corresponding to G, aug corresponding to x:T1, y:T2
	def augmentGamma(self, gamma, aug):
		augGamma = copy.deepcopy(gamma)
		augGamma.update(aug)
		return augGamma

	# Given a type t, return True if lin(t), false if un(t)
	def linType(self, type):
		if isinstance(type, PiCalcParser.TTypeContext):
			if isinstance(type, PiCalcParser.SessionTypeContext):
				if not isinstance(type.sType(), PiCalcParser.TerminateContext):
					return True

	def printDicts(self):
		print(self.gamma)
		print(self.typeNames)


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
		self.encodedStrBuilder = self.encodedStrBuilder.translate({ord(c): None for c in u"◼▲▼●⬥"})
		if self.errorStrBuilder == "":
			if (oldStr != self.encodedStrBuilder):
				self.errorStrBuilder = self.errorStrBuilder + "ERROR: The pi calculus could not be encoded. Please check that your input is valid.\n"
		if self.errorStrBuilder != "":
			self.encodedStrBuilder = ""
		return (self.encodedStrBuilder, self.warnStrBuilder, self.errorStrBuilder)


	## LISTENER METHODS

	## Encoding explanation:
	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## ◼ represents placeholder type declarations, 
	## ⬟ represents placeholder type annotations, ⭓ represents placeholder dual type annotations, ⬣ represent delayed placeholder type annotations
	## ▲ represents placeholder type, ▼ represents a placeholder type's dual,
	## ● represents a placeholder process, ⬥ represents a placeholder value


	def enterDeclAndProcs(self, ctx):
		if self.doEncoding:
			self.enterDeclAndProcsEnc(ctx)
	# Place single decl placeholder and single process placeholder, separated by two newlines
	def enterDeclAndProcsEnc(self, ctx):
		self.encodedStrBuilder = u"◼\n\n●"

	def enterDecls(self, ctx):
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
		if self.doEncoding:
			self.exitDeclsEnc(ctx)
	def exitDeclsEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])
			self.varNamesBackupStack.pop()


	def enterVariableAssignment(self, ctx):
		if self.doEncoding:
			self.enterVariableAssignmentEnc(ctx)
	# No type, so no change needed
	def enterVariableAssignmentEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", ctx.getText(), 1)


	def enterProcessNamingSes(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingSesEnc(ctx)
	# Place process placeholder
	def enterProcessNamingSesEnc(self, ctx):
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		decStr = ctx.name.text + "'(" + ctx.value().getText() + u" : ▲) := ●"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)

	def exitProcessNamingSes(self, ctx):
		if self.doEncoding:
			self.exitProcessNamingSesEnc(ctx)
	def exitProcessNamingSesEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterSessionTypeNaming(self, ctx):
		if self.doTypeChecking:
			self.enterSessionTypeNamingTCh(ctx)
		if self.doEncoding:
			self.enterSessionTypeNamingEnc(ctx)
	# Place type placeholder
	def enterSessionTypeNamingEnc(self, ctx):
		self.encFunc[ctx.name.text] = ctx.name.text + "'"
		decStr = "type " + ctx.name.text + u"' := ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterSessionTypeNamingTCh(self, ctx):
		self.typeNames[ctx.name.text] = ctx.tType().getText()

	def exitSessionTypeNaming(self, ctx):
		if self.doEncoding:
			self.exitSessionTypeNamingEnc(ctx)
	def exitSessionTypeNamingEnc(self, ctx):
		if self.varNamesBackupStack != []:
			self.usedVarNames = copy.deepcopy(self.varNamesBackupStack[-1])


	def enterSessionTypeDecl(self, ctx):
		if self.doTypeChecking:
			self.enterSessionTypeDeclTCh(ctx)
		if self.doEncoding:
			self.enterSessionTypeDeclEnc(ctx)
	# Place type placeholder
	def enterSessionTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterSessionTypeDeclTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.tType().getText()


	def enterSesTypeDeclAndAssign(self, ctx):
		if self.doTypeChecking:
			self.enterSessionTypeDeclTCh(ctx)
		if self.doEncoding:
			self.enterSesTypeDeclAndAssignEnc(ctx)
	# Place type placeholder
	def enterSesTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + u" ▲ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
	def enterSesTypeDeclAndAssignTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.tType().getText()


	def enterLinearTypeNaming(self, ctx):
		if self.doTypeChecking:
			self.enterLinearTypeNamingTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeNamingEnc(ctx)
	# Leave type declarations as is and display warning.
	def enterLinearTypeNamingEnc(self, ctx):
		decStr = "type " + ctx.name.text + " := " + ctx.linearType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinearTypeNamingTCh(self, ctx):
		self.typeNames[ctx.name.text] = ctx.linearType().getText()


	def enterLinearTypeDecl(self, ctx):
		if self.doTypeChecking:
			self.enterLinearTypeDeclTCh(ctx)
		if self.doEncoding:
			self.enterLinearTypeDeclEnc(ctx)
	# Leave linear type declarations as is and display warning.
	def enterLinearTypeDeclEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType.getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinearTypeDeclTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.linearType().getText()


	def enterLinTypeDeclAndAssign(self, ctx):
		if self.doTypeChecking:
			self.enterLinTypeDeclAndAssignTch(ctx)
		if self.doEncoding:
			self.enterLinTypeDeclAndAssignEnc(ctx)
	# Leave linear type declarations as is and display warning.
	def enterLinTypeDeclAndAssignEnc(self, ctx):
		decStr = "type " + ctx.var.text + " " + ctx.linearType.getText() + " = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"◼", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"
	def enterLinTypeDeclAndAssignTCh(self, ctx):
		self.gamma[ctx.var.text] = ctx.linearType().getText()



	def enterTermination(self, ctx):
		if self.doEncoding:
			self.enterTerminationEnc(ctx)
	# Termination encoded homomorphically
	def enterTerminationEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "0", 1)


	def enterNamedProcess(self, ctx):
		if self.doEncoding:
			self.enterNamedProcessEnc(ctx)
	# Process name encoded homomorphically, process itself already encoded when assigned name
	def enterNamedProcessEnc(self, ctx):
		nmStr = self.encodeName(ctx.name.text) + "(" + self.encodeName(ctx.value().getText()) + ")"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", nmStr, 1)


	def enterOutput(self, ctx):
		if self.doEncoding:
			self.enterOutputEnc(ctx)
	# Create new channel and send alongside encoded payload
	def enterOutputEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		newChan = self.generateChannelName()
		opStrBuilder = "(new " + newChan + u") (send(" + self.encodeName(ctx.channel.getText())
		if (len(ctx.payload)) > 1:
			self.errorStrBuilder = self.errorStrBuilder + "ERROR: send() cannot have multiple payloads in session pi calculus.\n"
		for pl in ctx.payload:
			opStrBuilder = opStrBuilder + ", " + self.encodeName(pl.getText())
		opStrBuilder = opStrBuilder + ", " + newChan + u").●)"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", opStrBuilder, 1)

	def exitOutput(self, ctx):
		if self.doEncoding:
			self.exitOutputEnc(ctx)
	def exitOutputEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterInputSes(self, ctx):
		if self.doEncoding:
			self.enterInputSesEnc(ctx)
	# Receive new channel alongside payloads
	def enterInputSesEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		ipStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + "," + ctx.payload.getText() + u" : ▲"
		newChan = self.generateChannelName()
		ipStrBuilder = ipStrBuilder + ", " + newChan + u").●"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", ipStrBuilder, 1)

	def exitInputSes(self, ctx):
		if self.doEncoding:
			self.exitInputSesEnc(ctx)
	def exitInputSesEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterSelection(self, ctx):
		if self.doEncoding:
			self.enterSelectionEnc(ctx)
	# Create new channel and send as variant value
	def enterSelectionEnc(self, ctx):
		self.checkBranchStack(False)
		self.checkCompStack(False)
		newChan = self.generateChannelName()
		selStr = "(new " + newChan + u") (send(" + self.encodeName(ctx.channel.getText()) + "," + ctx.selection.getText() + "_" + newChan + u").●)"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", selStr, 1)

	def exitSelection(self, ctx):
		if self.doEncoding:
			self.exitSelectionEnc(ctx)
	def exitSelectionEnc(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.compStack != []:
			self.compStack.pop()


	def enterBranching(self, ctx):
		if self.doEncoding:
			self.enterBranchingEnc(ctx)
	# Receive value then use for case statement
	def enterBranchingEnc(self, ctx):
		self.checkBranchStack(True)
		self.checkCompStack(False)
		caseVar = self.generateChannelName()
		brnStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + "," + caseVar + ").case " + caseVar + " of { \n"
		newChan = self.generateChannelName()
		for i in range(len(ctx.option)):
			brnStrBuilder = brnStrBuilder + "\t" + ctx.option[i].getText() + "_(" + newChan + ")" + " > " + u"●"
			if i != (len(ctx.option) - 1):
				brnStrBuilder = brnStrBuilder + ", \n"
			else:
				brnStrBuilder = brnStrBuilder + " }"
		self.encFunc[ctx.channel.getText()] = newChan
		self.encFuncBackupStack.append(copy.deepcopy(self.encFunc))
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		self.branchStack.append("B")
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", brnStrBuilder, 1)

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
		if self.doEncoding:
			self.enterCompositionEnc(ctx)
	# Composition encoded homomorpically
	def enterCompositionEnc(self, ctx):
		self.checkCompStack(True)
		self.varNamesBackupStack.append(copy.deepcopy(self.usedVarNames))
		self.compStack.append("C")
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"● | ●")

	def exitComposition(self, ctx):
		if self.doEncoding:
			self.exitCompositionEnc(ctx)
	def exitCompositionEnc(self, ctx):
		if self.compStack != []:
			self.compStack.pop()
		if self.varNamesBackupStack != []:
			self.varNamesBackupStack.pop()


	def enterSessionRestriction(self, ctx):
		if self.doEncoding:
			self.enterSessionRestrictionEnc(ctx)
	# Create new channel to replace both endpoints
	def enterSessionRestrictionEnc(self, ctx):
		newChan = self.generateChannelName()
		for ep in ctx.endpoint:
			self.encFunc[ep.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", "(new " + newChan + u" : ▲) (●)", 1)


	def enterChannelRestrictionSes(self, ctx):
		if self.doEncoding:
			self.enterChannelRestrictionSesEnc(ctx)
	# Channel Restriction encoded homomorphically
	def enterChannelRestrictionSesEnc(self, ctx):
		if not isinstance(ctx.tType(), PiCalcParser.ChannelTypeContext):
			self.errorStrBuilder = self.errorStrBuilder + "ERROR: Invalid type in channel restriction.\n"
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"(new ⬥ : ▲) (●)", 1)


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
				typeStrBuilder = typeStrBuilder + ", \n\t"
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
				typeStrBuilder = typeStrBuilder + ", \n\t"
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
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", u"#▲", 1)

	def enterUnitType(self, ctx):
		if self.doEncoding:
			self.enterUnitTypeEnc(ctx)
	def enterUnitTypeEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "Unit", 1)

	def enterBoolean(self, ctx):
		if self.doEncoding:
			self.enterBooleanEnc(ctx)
	def enterBooleanEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "Bool", 1)

	def enterInteger(self, ctx):
		if self.doEncoding:
			self.enterIntegerEnc(ctx)
	def enterIntegerEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "Int", 1)

	def enterString(self, ctx):
		if self.doEncoding:
			self.enterStringEnc(ctx)
	def enterStringEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"▲", "String", 1)




	# Raise error if linear version of input is used
	def enterInputLin(self, ctx):
		if self.doEncoding:
			self.enterInputLinEnc(ctx)
	def enterInputLinEnc(self, ctx):
		self.errorStrBuilder = self.errorStrBuilder + "ERROR: Receive statements containing linear types and/or multiple payloads are not supported in session pi calculus.\n"

	def enterProcessNamingLin(self, ctx):
		if self.doEncoding:
			self.enterProcessNamingLinEnc(ctx)
	# Raise error if linear version of process naming is used
	def enterProcessNamingLinEnc(self, ctx):
		self.errorStrBuilder = self.errorStrBuilder + "ERROR: Process naming containing linear types are not supported in session pi calculus.\n"

	def enterChannelRestrictionLin(self, ctx):
		if self.doEncoding:
			self.enterChannelRestrictionLinEnc(ctx)
	# Raise error if linear version of channel restriction is used
	def enterChannelRestrictionLinEnc(self, ctx):
		self.errorStrBuilder = self.errorStrBuilder + "ERROR: Channel restrictions containing linear types are not supported in session pi calculus.\n"


	def enterCase(self, ctx):
		if self.doEncoding:
			self.enterCaseEnc(ctx)
	# Case is not native to session pi calculus, so encode homomorphically and display warning
	def enterCaseEnc(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace(u"●", u"case ⬥ of {⬥ > ●, ⬥ > ●}", 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Case statements are not native to session pi calculus.\n"


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