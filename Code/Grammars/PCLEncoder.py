from antlr4 import *
from PiCalcListener import PiCalcListener

class PCLEncoder(PiCalcListener):

	def __init__(self):
		self.encodedStrBuilder = "&"

	## Reconstruct the string using temporary placeholders to ensure correct placement
	## Since enter___ methods traverse tree in pre-order, desired process/value should be first placeholder, 
	## so calling replace() with max = 1 should replace the correct placeholder
	## & represents a placeholder process, % represents a placeholder value

	# Enter a parse tree produced by PiCalcParser#Branching.
	def enterBranching(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "branch(%){%:&, %:&}", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Branching.
	def exitBranching(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Input.
	def enterInput(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "receive(%, %).&", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Input.
	def exitInput(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Composition.
	def enterComposition(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "& | &")

	# Exit a parse tree produced by PiCalcParser#Composition.
	def exitComposition(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#ChannelRestriction.
	def enterChannelRestriction(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "(new %) &", 1)

	# Exit a parse tree produced by PiCalcParser#ChannelRestriction.
	def exitChannelRestriction(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#SessionRestriction.
	def enterSessionRestriction(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "(new %%) &", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#SessionRestriction.
	def exitSessionRestriction(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Selection.
	def enterSelection(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "select(%,%).&", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Selection.
	def exitSelection(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Output.
	def enterOutput(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "send(%,%).&", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Output.
	def exitOutput(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Termination.
	def enterTermination(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "0", 1)

	# Exit a parse tree produced by PiCalcParser#Termination.
	def exitTermination(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Case.
	def enterCase(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("&", "case % of {% > &, % > &}", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Case.
	def exitCase(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#UnitValue.
	def enterUnitValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "*", 1)

	# Exit a parse tree produced by PiCalcParser#UnitValue.
	def exitUnitValue(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#Name.
	def enterName(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", ctx.getText(), 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#Name.
	def exitName(self, ctx):
		pass


	# Enter a parse tree produced by PiCalcParser#VariantValue.
	def enterVariantValue(self, ctx):
		self.encodedStrBuilder = self.encodedStrBuilder.replace("%", "l_%", 1)
		## Temporarily treating as homomorphism to check string reconstruction works

	# Exit a parse tree produced by PiCalcParser#VariantValue.
	def exitVariantValue(self, ctx):
		pass

	def getEncodedString(self):
		return self.encodedStrBuilder