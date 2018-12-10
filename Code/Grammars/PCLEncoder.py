# encoding: utf-8
from antlr4 import *
from PiCalcListener import PiCalcListener
import copy

class PCLEncoder(PiCalcListener):

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
	def __init__(self, varNameList):
		self.encodedStrBuilder = ""
		self.warnStrBuilder = ""
		self.errorStrBuilder = ""
		self.encFunc = {}
		self.usedVarNames = varNameList
		self.branchStack = []
		self.encFuncBackupStack = []

	# Generate a new channel name for the encoding function
	# In theory, this function can generate up to 26^2 i.e. 676 channel names
	# It is very unlikely this limit would ever be reached accidentally.
	# A warning is displayed once it has attempted to generate more than 26 names
	def generateChannelName(self):
		chan = 'a'															# Start at a
		chansuffix = chan[-1:]												# Get last char of chan
		while chan in self.usedVarNames:									# if channel name already exists, iterate last character
			if chansuffix == 'z':											# if last character z
				if chansuffix == chan:										# and channel name is single char
					chan = 'aA'												# Jump to aA and display warning
					self.warnStrBuilder = self.warnStrBuilder + "WARNING: The encoding has made a large amount of attempts to generate new channel names and may be unclear. If possible, please reduce the amount of single-letter variable names you are using.\n"
				else:														# if channel name multiple chars
					chan = chan[:-2] + chr(ord(chan[-2]) + 1) + 'a'			# iterate 2nd last character and set last char to a
			else:
				chan = chan[:-1] + chr(ord(chan[-1:]) + 1)
		self.usedVarNames.append(chan)										# add to list of existing variable names
		return chan

	def encodeName(self, name):
		if name == '*':
			return '*'
		return self.encFunc.get(name, name)

	def checkBranchStack(self, channel):
		if self.branchStack != []:
			if self.branchStack[-1] != 'B':
				self.branchStack.append('C')
			else:
				if self.encFuncBackupStack != []:
					self.encFunc = copy.deepcopy(self.encFuncBackupStack[-1])
				self.branchStack.append('C')

	def getEncoding(self):
		# Attempt to remove any leftover placeholders, and display error if anything was removed 
		oldStr = self.encodedStrBuilder
		self.encodedStrBuilder = self.encodedStrBuilder.translate({ord(c): None for c in u'@$£^%'})
		if (oldStr != self.encodedStrBuilder):
			self.errorStrBuilder = self.errorStrBuilder + "ERROR: There seems to have been a problem with the encoding. Please check that your input is valid.\n"
		return (self.encodedStrBuilder, self.warnStrBuilder, self.errorStrBuilder)


	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## @ represents placeholder type declarations, $ represents placeholder type, £ represents a placeholder type's dual,
	## ^ represents a placeholder process, % represents a placeholder value


	# If just processes, place single process placeholder
	def enterJustProcesses(self, ctx):
		self.encodedStrBuilder = "^"


	# If just declarations, place single decl placeholder
	def enterJustDeclarations(self, ctx):
		self.encodedStrBuilder = "@"


	# If decls and processes, place single decl placeholder and single process placeholder, separated by two newlines
	def enterDeclAndProcs(self, ctx):
		self.encodedStrBuilder = "@\n\n^"


	# Replace single decl placeholder as placed by enterDeclAndProcs above, with placeholders for each declaration
	def enterDecls(self, ctx):
		if len(ctx.decs) > 1:
			decPlaceholderStr = ""
			for i in range(len(ctx.decs)):
				if i != (len(ctx.decs) - 1):
					decPlaceholderStr = decPlaceholderStr + "@,\n"
				else:
					decPlaceholderStr = decPlaceholderStr + "@\n"
			self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decPlaceholderStr, 1)


	# No type, so no change needed
	def enterVariableAssignment(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", ctx.getText(), 1)


	# Place process placeholder
	def enterProcessNaming(self, ctx):
		decStr = ctx.ID().getText() + " := ^"
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)


	# Place type placeholder
	def enterSessionTypeDecl(self, ctx):
		decStr = "type " + ctx.ID().getText() + " $"
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)



	# Place type placeholder
	def enterSesTypeDeclAndAssign(self, ctx):
		decStr = "type " + ctx.ID().getText() + " $ = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)


	# Basic types encoded homomorphically
	def enterBasicTypeDecl(self, ctx):
		decStr = "type " + ctx.ID().getText() + " " + ctx.basicType().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)


	# Basic types encoded homomorphically
	def enterBasicTypeDeclAndAssign(self, ctx):
		decStr = "type " + ctx.ID().getText() + " " + ctx.basicType().getText() + " = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)


	# Leave linear type declarations as is and display warning.
	def enterLinearTypeDecl(self, ctx):
		decStr = "type " + ctx.ID().getText() + " " + ctx.linearType.getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"


	# Leave linear type declarations as is and display warning.
	def enterLinTypeDeclAndAssign(self, ctx):
		decStr = "type " + ctx.ID().getText() + " " + ctx.linearType.getText() + " = " + ctx.value().getText()
		self.encodedStrBuilder = self.encodedStrBuilder.replace("@", decStr, 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Linear type declarations found in session pi calculus.\n"



	# Termination encoded homomorphically
	def enterTermination(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", "0", 1)


	# Process name encoded homomorphically, process itself already encoded when assigned name
	def enterNamedProcess(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", ctx.ID().getText(), 1)


	# Create new channel and send alongside encoded payloads
	def enterOutput(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		newChan = self.generateChannelName()
		opStrBuilder = '(new ' + newChan + ')send(' + self.encodeName(ctx.channel.getText())
		for pl in ctx.payload:
			opStrBuilder = opStrBuilder + "," + self.encodeName(pl.getText())
		opStrBuilder = opStrBuilder + ',' + newChan + ').^'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", opStrBuilder, 1)

	def exitOutput(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Receive new channel alongside payloads
	def enterInput(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		ipStrBuilder = "receive(" + self.encodeName(ctx.channel.getText())
		for pl in ctx.payload:
			ipStrBuilder = ipStrBuilder + "," + pl.getText()
		newChan = self.generateChannelName()
		ipStrBuilder = ipStrBuilder + ',' + newChan + ').^'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", ipStrBuilder, 1)

	def exitInput(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Create new channel and send as variant value
	def enterSelection(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		newChan = self.generateChannelName()
		selStr = '(new ' + newChan + ')send(' + self.encodeName(ctx.channel.getText()) + "," + ctx.selection.getText() + "_" + newChan + ').^'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", selStr, 1)

	def exitSelection(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Receive value then use for case statement
	def enterBranching(self, ctx):
		caseVar = self.generateChannelName()
		brnStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + ',' + caseVar + ').case ' + caseVar + ' of { '
		newChan = self.generateChannelName()
		for i in range(len(ctx.option)):
			brnStrBuilder = brnStrBuilder + ctx.option[i].getText() + '_(' + newChan + ')' + ' > ' + '^'
			if i != (len(ctx.option) - 1):
				brnStrBuilder = brnStrBuilder + ', '
			else:
				brnStrBuilder = brnStrBuilder + ' }'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encFuncBackupStack.append(copy.deepcopy(self.encFunc))
		self.branchStack.append("B")
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", brnStrBuilder, 1)

	def exitBranching(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.encFuncBackupStack != []:
			self.encFuncBackupStack.pop()


	# Composition encoded homomorpically
	def enterComposition(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", "^ | ^")


	# Create new channel to replace both endpoints
	def enterSessionRestriction(self, ctx):
		newChan = self.generateChannelName()
		for ep in ctx.endpoint:
			self.encFunc[ep.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", "(new " + newChan + ")^", 1)


	## Since £ represents a placeholder dualed type, if encodedStrBuilder contains a £ before a $,
	## the next type must be encoded as its dual instead.
	## Due to the properites of the encoding of dual types,
	## This only changes whether the channel is linear input or linear output
	## How the next type, i.e. S in ?T.S or !T.S, is encoded is not affected

	def isNextDual(self):
		firstType = self.encodedStrBuilder.find("$")
		firstDual = self.encodedStrBuilder.find(u"£")
		return firstDual != -1 and (firstType == -1 or firstDual < firstType)

	# Encode terminate as channel with no capabilities
	def enterTerminate(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"£", "/[]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "/[]", 1)


	# Encode a receive as a linear input
	def enterReceive(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"£", "lo[$, $]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "li[$, $]", 1)


	# Encode a send as a linear output, with the dual of the sType
	def enterSend(self, ctx):
		if self.isNextDual():
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"£", u"li[$, £]", 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace("$", u"lo[$, £]", 1)


	# Encode a branch as a linear input of a variant value
	def enterBranch(self, ctx):
		dual = self.isNextDual()
		if dual:
			typeStrBuilder = "lo[<"
		else:
			typeStrBuilder = "li[<"
		for i in range(len(ctx.option)):
			typeStrBuilder = typeStrBuilder + ctx.option[i].getText() + "_$"
			if i != (len(ctx.option) - 1):
				typeStrBuilder = typeStrBuilder + ", "
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"£", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace("$", typeStrBuilder, 1)


	# Encode a select as a linear output of a variant value, with the dual of the sTypes
	def enterSelect(self, ctx):
		dual = self.isNextDual()
		if dual:
			typeStrBuilder = "li[<"
		else:
			typeStrBuilder = "lo[<"
		for i in range(len(ctx.option)):
			typeStrBuilder = typeStrBuilder + ctx.option[i].getText() + u"_£"
			if i != (len(ctx.option) - 1):
				typeStrBuilder = typeStrBuilder + ", "
			else:
				typeStrBuilder = typeStrBuilder + ">]"
		if dual:
			self.encodedStrBuilder = self.encodedStrBuilder.replace(u"£", typeStrBuilder, 1)
		else:
			self.encodedStrBuilder = self.encodedStrBuilder.replace("$", typeStrBuilder, 1)


	# Encode basic types homomorphically

	def enterUnitType(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "Unit", 1)

	def enterBoolean(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "Bool", 1)

	def enterInteger(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "Int", 1)

	def enterString(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("$", "String", 1)





	# Channel Restriction encoded homomorphically
	def enterChannelRestriction(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", "(new %) ^", 1)


	# Case is not native to session pi calculus, so encode homomorphically and display warning
	def enterCase(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("^", "case % of {% > ^, % > ^}", 1)
		self.warnStrBuilder = self.warnStrBuilder + "WARNING: Case statements are not native to session pi calculus.\n"


	# Unit value encoded homomorphically
	def enterUnitValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "*", 1)


	# In theory, may be unneeded?
	def enterName(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", ctx.getText(), 1)


	# In theory, may be unneeded? Variant value also not native to session pi calculus
	def enterVariantValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "l_%", 1)