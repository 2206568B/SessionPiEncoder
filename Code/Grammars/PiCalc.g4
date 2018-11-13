grammar PiCalc;

process	: '0'																			# Termination
		| 'send(' value ',' value ').' process											# Output
		| 'receive(' value ',' value ').' process										# Input
		| process '|' process															# Composition
		| '(new ' value ')' process														# ChannelRestriction
		/** Case and Branching must give two or more options, hence '(...)+ ...' structure */
		/** Below rules are for linear pi Calculus */
		| 'case ' value ' of {' (value '>' process ',')+ value '>' process '}'			# Case
		/** Below rules are for session pi calculus */
		| '(new ' value value ')' process												# SessionRestriction
		| 'branch(' value '){' (value ':' process ',')+ value ':' process '}'			# Branching
		| 'select(' value ',' value ').' process										# Selection
		;

value	: '*'																			# UnitValue
		| ID																			# Name
		| ID '_' value																	# VariantValue
		;

ID		: [a-z]+ ;
WS		: [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines