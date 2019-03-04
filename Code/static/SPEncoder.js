$(document).ready(function() {
	$('#encode').click(function(){
		$('div#sepi-term').html('Typechecking and encoding...');
		$.getJSON($SCRIPT_ROOT + '/encode', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			$('textarea#lipi').val(data.encoded);
			$('#run-lipi').prop('disabled', false);
			$('#tc-lipi').prop('disabled', false);
			if(data.output !== "") {
				$('div#sepi-term').html(data.output);
				$('div#lipi-term').text("");
			}
		});
		return false;
	});
	$('#run-sepi').click(function(){
		$('div#sepi-term').html('Typechecking and executing...');
		$.getJSON($SCRIPT_ROOT + '/run_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#sepi-term').html(data.output);
			}
		});
		return false;
	});
	$('#run-lipi').click(function(){
		$('div#lipi-term').html('Typechecking and executing...');
		$.getJSON($SCRIPT_ROOT + '/run_lipi', {
			lipi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.result != "") {
				$('div#lipi-term').html(data.output);
			}
		});
		return false;
	});
	$('#tc-sepi').click(function(){
		$('div#sepi-term').html('Typechecking...');
		$.getJSON($SCRIPT_ROOT + '/tc_sepi', {
			sepi_code: $('textarea#sepi').val()
		}, function(data) {
			if(data.output != "") {
				$('div#sepi-term').html(data.output);
			}
		});
		return false;
	});
	$('#tc-lipi').click(function(){
		$('div#lipi-term').html('Typechecking...');
		$.getJSON($SCRIPT_ROOT + '/tc_lipi', {
			sepi_code: $('textarea#lipi').val()
		}, function(data) {
			if(data.output != "") {
				$('div#lipi-term').html(data.output);
			}
		});
		return false;
	});
	$('textarea#sepi').keyup(function(){
		if ($('textarea#sepi').val().length > 0) {
			$('#run-sepi').prop('disabled', false);
			$('#tc-sepi').prop('disabled', false);
			$('#encode').prop('disabled', false);
		} else {
			$('#run-sepi').prop('disabled', true);
			$('#tc-sepi').prop('disabled', true);
			$('#encode').prop('disabled', true);
		}
	});
	$('textarea#lipi').keyup(function(){
		if ($('textarea#lipi').val().length > 0) {
			$('#run-lipi').prop('disabled', false);
			$('#tc-lipi').prop('disabled', false);
		} else {
			$('#run-lipi').prop('disabled', true);
			$('#tc-lipi').prop('disabled', true);
		}
	});
});
