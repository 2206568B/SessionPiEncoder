from antlr4 import *
from PiCalcListener import PiCalcListener

class VariableNameCollector(PiCalcListener):

	def __init__(self):
		self.varNameList = []

	## Parse pi calc to find all user-made variable names
	## to prevent collisions from encoding-generated names
	## This should be run before PCLEncoder

	# When variable anem found, add to list
	def enterName(self, ctx):
		if not (ctx.getText() in self.varNameList):
			self.varNameList.append(ctx.getText())

	# Return list of variable names
	def getVarNameList(self):
		return self.varNameList