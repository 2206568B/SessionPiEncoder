from flask import Flask, render_template, jsonify, request
from antlr4 import *
from Grammars.PiCalcLexer import PiCalcLexer
from Grammars.PiCalcParser import PiCalcParser
from Grammars.SPEListener import SPEListener
from Grammars.SPERunner import SPERunner
from Grammars.VariableNameCollector import VariableNameCollector

import sys

app = Flask(__name__)

@app.route("/")
def main_page():
	return render_template("SPEncoder.html")

@app.route("/encode")
def encode():
	code = request.args.get('sepi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	varNameColl = VariableNameCollector({})
	varWalker = ParseTreeWalker()
	varWalker.walk(varNameColl, tree)
	varNames = varNameColl.getVarNameList()
	listener = SPEListener(True, False, True, varNames)
	listener.doOperations(tree)
	tcStr, tcErr = listener.getTypeCheckResults()
	if tcErr != "":
		return jsonify(encoded = "", output = tcErr)
	else:
		encStr, encErr = listener.getEncoding()
		if encErr != "":
			outputStr = tcStr + encErr
			return jsonify(encoded = encStr, output = outputStr)
		else:
			outputStr = tcStr + "<span class='success'>Encoding succesful.</span>\n"
			return jsonify(encoded = encStr, output = outputStr)
			

@app.route("/run_sepi")
def run_sepi():
	code = request.args.get('sepi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	listener = SPEListener(True, False, False, [])
	listener.doOperations(tree)
	tcStr, tcErr = listener.getTypeCheckResults()
	if tcErr != "":
		return jsonify(encoded = "", output = tcErr)
	else:
		runner = SPERunner(True, False)
		runner.doExecution(tree)
		exStr, exErr = runner.getExecutionResults()
		outputStr = tcStr + tcErr + exStr + exErr
		return jsonify(output = outputStr)

@app.route("/run_lipi")
def run_lipi():
	code = request.args.get('lipi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	listener = SPEListener(False, True, False, [])
	listener.doOperations(tree)
	tcStr, tcErr = listener.getTypeCheckResults()
	if tcErr != "":
		return jsonify(encoded = "", output = tcErr)
	else:
		runner = SPERunner(False, True)
		runner.doExecution(tree)
		exStr, exErr = runner.getExecutionResults()
		outputStr = tcStr + tcErr + exStr + exErr
		return jsonify(output = outputStr)

@app.route("/tc_sepi")
def tc_sepi():
	code = request.args.get('sepi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	listener = SPEListener(True, False, False, [])
	listener.doOperations(tree)
	tcStr, tcErr = listener.getTypeCheckResults()
	outputStr = tcStr + tcErr
	return jsonify(output = outputStr)

@app.route("/tc_lipi")
def tc_lipi():
	code = request.args.get('sepi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	listener = SPEListener(False, True, False, [])
	listener.doOperations(tree)
	tcStr, tcErr = listener.getTypeCheckResults()
	outputStr = tcStr + tcErr
	return jsonify(output = outputStr)