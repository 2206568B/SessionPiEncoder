$(document).ready(function() {
	$('#encode').click(function(){
		$.getJSON($SCRIPT_ROOT + '/encode', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			$('textarea#lipi').val(data.encoded);
			if(data.output !== "") {
				$('div#sepi-term').text(data.output);
			}
		});
		return false;
	});
	$('#run-sepi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#sepi-term').text(data.result);
			}
		});
		return false;
	});
	$('#run-lipi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/run_lipi', {
			lipi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#lipi-term').text(data.result);
			}
		});
		return false;
	});
	$('#tc-sepi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/tc_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.output != "") {
				$('div#sepi-term').text(data.output);
			}
		});
		return false;
	});
	$('#tc-lipi').click(function(){
		$.getJSON($SCRIPT_ROOT + '/tc_lipi', {
			sepi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.output != "") {
				$('div#lipi-term').text(data.output);
			}
		});
		return false;
	});
});