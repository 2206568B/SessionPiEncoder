from flask import Flask, render_template, jsonify, request
from antlr4 import *
from Grammars.PiCalcLexer import PiCalcLexer
from Grammars.PiCalcParser import PiCalcParser
from Grammars.SPEListener import SPEListener
from Grammars.VariableNameCollector import VariableNameCollector

import sys

app = Flask(__name__)

@app.route("/")
def main_page():
	return render_template("SPEncoder.html")

@app.route("/encode")
def encode():
	code = request.args.get('sepi_code', "", type=str)
#	try:
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	varNameColl = VariableNameCollector()
	varWalker = ParseTreeWalker()
	varWalker.walk(varNameColl, tree)
	varNames = varNameColl.getVarNameList()
	listener = SPEListener(True, True, varNames)
	walker = ParseTreeWalker()
	walker.walk(listener, tree)
	encStr, warn, err = listener.getEncoding()
	#listener.printDicts()
#	except:
#		encStr, warn, err = "", "", "ERROR: The encoding seems to have failed. Please check that your input is valid."
	return jsonify(encoded = encStr, warnings = warn, errors = err)

@app.route("/run_sepi")
def run_sepi():
	code = request.args.get('sepi_code', "", type=str)
	return jsonify(result = code)

@app.route("/run_lipi")
def run_lipi():
	code = request.args.get('lipi_code', "", type=str)
	return jsonify(result = code)