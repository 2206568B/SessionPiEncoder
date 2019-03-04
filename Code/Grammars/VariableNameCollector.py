from antlr4 import *
from PiCalcListener import PiCalcListener

class VariableNameCollector(PiCalcListener):

	def __init__(self, delProcs):
		self.varNameList = []
		self.capabilityList = []
		self.delayedProcesses = delProcs

	## Parse pi calc to find all user-made variable names
	## to prevent collisions from encoding-generated names
	## This should be run before SPEListener

	# When linear-typed send found, add variable name and output capability to list
	def enterOutput(self, ctx):
		tempDict = dict(self.capabilityList)
		if ctx.channel.getText() in tempDict and tempDict[ctx.channel.getText()] == "Input":
			self.capabilityList.remove((ctx.channel.getText(), "Input"))
			self.capabilityList.append((ctx.channel.getText(), "Both"))
		elif ctx.channel.getText() not in tempDict:
			self.capabilityList.append((ctx.channel.getText(), "Output"))

	# When linear-typed receive found, add variable name and input capability to list
	def enterInputLin(self, ctx):
		tempDict = dict(self.capabilityList)
		if ctx.channel.getText() in tempDict and tempDict[ctx.channel.getText()] == "Output":
			self.capabilityList.remove((ctx.channel.getText(), "Output"))
			self.capabilityList.append((ctx.channel.getText(), "Both"))
		elif ctx.channel.getText() not in tempDict:
			self.capabilityList.append((ctx.channel.getText(), "Input"))

	# When named process found, traverse saved process from declaration
	def enterNamedProcess(self, ctx):
		if self.delayedProcesses != {}:
			(delayChan, delayType, delayProc) = self.delayedProcesses[ctx.name.text]
			procWalker = ParseTreeWalker()
			procWalker.walk(self, delayProc)
			for chanCap in self.capabilityList:
				if chanCap[0] == delayChan.getText():
					self.capabilityList.append((delayChan.getText(), chanCap[1]))
					self.capabilityList.remove(chanCap)


	# When variable name found, add to list
	def enterNamedValue(self, ctx):
		if not (ctx.getText() in self.varNameList):
			self.varNameList.append(ctx.getText())
		tempDict = dict(self.capabilityList)
		if ctx.getText() not in tempDict:
			self.capabilityList.append((ctx.getText(), ""))

	# Return list of variable names
	def getVarNameList(self):
		return self.varNameList

	# Return list of capabilities
	def getCapabilityList(self):
		return self.capabilityList