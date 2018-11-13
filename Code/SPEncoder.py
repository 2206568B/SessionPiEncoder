from flask import Flask, render_template, jsonify, request
from antlr4 import *
from Grammars.PiCalcLexer import PiCalcLexer
from Grammars.PiCalcParser import PiCalcParser
from Grammars.PCLEncoder import PCLEncoder

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
	tree = parser.process()
	printer = PCLEncoder()
	walker = ParseTreeWalker()
	walker.walk(printer, tree)
	encStr = printer.getEncodedString()
	return jsonify(encoded = encStr)

@app.route("/run_sepi")
def run_sepi():
	code = request.args.get('sepi_code', "", type=str)
	return jsonify(result = code)

@app.route("/run_lipi")
def run_lipi():
	code = request.args.get('lipi_code', "", type=str)
	return jsonify(result = code)