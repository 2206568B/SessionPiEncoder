grammar PiCalc;

process	: '0'																			# Termination
		| 'send(' value ', ' value ').' process											# Output
		| 'receive(' value ', ' value ').' process										# Input
		| process '|' process															# Composition
		| '(new ' value ')' process														# Channel Restriction
		/** Case and Branching must give two or more options, hence '(...)+ ...' structure */
		/** Below rules are for linear pi Calculus */
		| 'case ' value ' of {' (value '>' process ', ')+ value '>' process '}'			# Case
		/** Below rules are for session pi calculus */
		| '(new ' value value ')' process												# Session Restriction
		| 'branch(' value ') {' (value ' : ' process ', ')+ value ' : ' process '}'		# Branching
		| 'select(' value ', ' value ').' process										# Selection
		;

value	: '*'																			# Unit Value
		| ID																			# Name
		| ID '_' value																	# Variant Value
		;

ID		: [a-z]+ ;