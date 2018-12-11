$(document).ready(function() {
	$('#encode').click(function(){
		$.getJSON($SCRIPT_ROOT + '/encode', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			$('textarea#lipi').val(data.encoded);
			if(data.warnings !== "" || data.errors !== "") {
				$('div#sepi-term').text($('div#sepi-term').text() + '\n' + data.warnings + data.errors);
			}
		});
		return false;
	});
	$('#run-sepi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#sepi-term').text($('div#sepi-term').text() + '\n' + data.result);
			}
		});
		return false;
	});
	$('#run-lipi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_lipi', {
			lipi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#lipi-term').text($('div#lipi-term').text() + '\n' + data.result);
			}
		});
		return false;
	});
});