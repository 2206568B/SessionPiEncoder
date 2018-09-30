from flask import Flask, render_template, jsonify, request
app = Flask(__name__)

@app.route("/")
def main_page():
	return render_template("SPEncoder.html")

# AJAX code for buttons, dummy code for now
@app.route("/encode")
def encode():
	code = request.args.get('sepi_code', "", type=str)
	return jsonify(encoded = "[[" + code + "]]")

@app.route("/run_sepi")
def run_sepi():
	code = request.args.get('sepi_code', "", type=str)
	return jsonify(result = code)

@app.route("/run_lipi")
def run_lipi():
	code = request.args.get('lipi_code', "", type=str)
	return jsonify(result = code)