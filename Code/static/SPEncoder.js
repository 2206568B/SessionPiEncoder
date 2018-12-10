$(document).ready(function() {
	$('#encode').click(function(){
		$.getJSON($SCRIPT_ROOT + '/encode', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			$('textarea#lipi').val(data.encoded);
			if(data.warnings !== "" || data.errors !== "") {
				$('div#sepi-terminal').text($('div#sepi-terminal').text() + '\n' + data.warnings + data.errors);
			}
		});
		return false;
	});
	$('#run-sepi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#sepi-terminal').text($('div#sepi-terminal').text() + '\n' + data.result);
			}
		});
		return false;
	});
	$('#run-lipi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_lipi', {
			lipi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#lipi-terminal').text($('div#lipi-terminal').text() + '\n' + data.result);
			}
		});
		return false;
	});
});