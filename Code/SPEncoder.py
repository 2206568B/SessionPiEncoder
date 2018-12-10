from flask import Flask, render_template, jsonify, request
from antlr4 import *
from Grammars.PiCalcLexer import PiCalcLexer
from Grammars.PiCalcParser import PiCalcParser
from Grammars.PCLEncoder import PCLEncoder
from Grammars.VariableNameCollector import VariableNameCollector

app = Flask(__name__)

@app.route("/")
def main_page():
	return render_template("SPEncoder.html")

# AJAX code for buttons, dummy code for now
@app.route("/encode")
def encode():
	code = request.args.get('sepi_code', "", type=str)
	lexer_input = InputStream(code)
	lexer = PiCalcLexer(lexer_input)
	stream = CommonTokenStream(lexer)
	parser = PiCalcParser(stream)
	tree = parser.encInput()
	varNameColl = VariableNameCollector()
	varWalker = ParseTreeWalker()
	varWalker.walk(varNameColl, tree)
	varNames = varNameColl.getVarNameList()
	printer = PCLEncoder(varNames)
	walker = ParseTreeWalker()
	walker.walk(printer, tree)
	encStr, warn, err = printer.getEncoding()
	return jsonify(encoded = encStr, warnings = warn, errors = err)

@app.route("/run_sepi")
def run_sepi():
	code = request.args.get('sepi_code', "", type=str)
	return jsonify(result = code)

@app.route("/run_lipi")
def run_lipi():
	code = request.args.get('lipi_code', "", type=str)
	return jsonify(result = code)