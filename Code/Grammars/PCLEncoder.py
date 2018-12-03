# coding=utf-8
from antlr4 import *
from PiCalcListener import PiCalcListener
import copy

class PCLEncoder(PiCalcListener):

	## encodedStrBuilder is used to reconstruct the pi calc string.
	## warnBuilder is used to construct warning messages
	## errorBuilder is used to construct error messages
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
		self.encodedStrBuilder = "&"
		self.warnBuilder = ""
		self.errorBuilder = ""
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
					chan = 'cA'												# Jump to cA and display warning
					self.warnBuilder = self.warnBuilder + "WARNING: The encoding has made a large amount of attempts to generate new channel names and may be unclear. If possible, please reduce the amount of single-letter variable names you are using.\n"
				else:														# if channel name multiple chars
					chan = chan[:-2] + chr(ord(chan[-2] + 1)) + 'a'			# iterate 2nd last character and set last char to a
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
		return (self.encodedStrBuilder, self.warnBuilder, self.errorBuilder)


	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## & represents a placeholder process, % represents a placeholder value


	# Enter a parse tree produced by PiCalcParser#Termination.
	def enterTermination(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "0", 1)


	# Enter a parse tree produced by PiCalcParser#Output.
	def enterOutput(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		newChan = self.generateChannelName()
		opStrBuilder = '(new ' + newChan + ')send(' + self.encodeName(ctx.channel.getText())
		for pl in ctx.payload:
			opStrBuilder = opStrBuilder + "," + self.encodeName(pl.getText())
		opStrBuilder = opStrBuilder + ',' + newChan + ').&'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", opStrBuilder, 1)

	def exitOutput(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Enter a parse tree produced by PiCalcParser#Input.
	def enterInput(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		ipStrBuilder = "receive(" + self.encodeName(ctx.channel.getText())
		for pl in ctx.payload:
			ipStrBuilder = ipStrBuilder + "," + pl.getText()
		newChan = self.generateChannelName()
		ipStrBuilder = ipStrBuilder + ',' + newChan + ').&'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", ipStrBuilder, 1)

	def exitInput(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Enter a parse tree produced by PiCalcParser#Selection.
	def enterSelection(self, ctx):
		self.checkBranchStack(ctx.channel.getText())
		newChan = self.generateChannelName()
		selStr = '(new ' + newChan + ')send(' + self.encodeName(ctx.channel.getText()) + "," + ctx.selection.getText() + "_" + newChan + ').&'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", selStr, 1)

	def exitSelection(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()


	# Enter a parse tree produced by PiCalcParser#Branching.
	def enterBranching(self, ctx):
		caseVar = self.generateChannelName()
		brnStrBuilder = "receive(" + self.encodeName(ctx.channel.getText()) + ',' + caseVar + ').case ' + caseVar + ' of { '
		newChan = self.generateChannelName()
		for i in range(len(ctx.option)):
			brnStrBuilder = brnStrBuilder + ctx.option[i].getText() + '_(' + newChan + ')' + ' > ' + '&'
			if i != (len(ctx.option) - 1):
				brnStrBuilder = brnStrBuilder + ', '
			else:
				brnStrBuilder = brnStrBuilder + ' }'
		self.encFunc[ctx.channel.getText()] = newChan
		self.encFuncBackupStack.append(copy.deepcopy(self.encFunc))
		self.branchStack.append("B")
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", brnStrBuilder, 1)

	def exitBranching(self, ctx):
		if self.branchStack != []:
			self.branchStack.pop()
		if self.encFuncBackupStack != []:
			self.encFuncBackupStack.pop()

	# Enter a parse tree produced by PiCalcParser#Composition.
	def enterComposition(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "& | &")


	# Enter a parse tree produced by PiCalcParser#SessionRestriction.
	def enterSessionRestriction(self, ctx):
		newChan = self.generateChannelName()
		for ep in ctx.endpoint:
			self.encFunc[ep.getText()] = newChan
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "(new " + newChan + ")&", 1)





	# Enter a parse tree produced by PiCalcParser#ChannelRestriction.
	def enterChannelRestriction(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "(new %) &", 1)


	# Enter a parse tree produced by PiCalcParser#Case.
	def enterCase(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "case % of {% > &, % > &}", 1)
		self.warnBuilder = self.warnBuilder + "WARNING: Case statements are not native to session pi calculus.\n"
		## Case is not native to session pi calculus, so encode homomorphically and print warning


	# Enter a parse tree produced by PiCalcParser#UnitValue.
	def enterUnitValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "*", 1)


	# Enter a parse tree produced by PiCalcParser#Name.
	def enterName(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", ctx.getText(), 1)
		## Temporarily treating as homomorphism to check string reconstruction works


	# Enter a parse tree produced by PiCalcParser#VariantValue.
	def enterVariantValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "l_%", 1)
		## Temporarily treating as homomorphism to check string reconstruction works