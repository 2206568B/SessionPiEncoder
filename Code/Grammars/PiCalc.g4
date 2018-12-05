grammar PiCalc;

/** Declarations and Assignments */

declAssign  : ID ':=' process                                                                                                     # ProcessNaming
            | ID '=' value                                                                                                        # VariableAssignment
            | 'type ' ID linearType                                                                                               # LinearTypeDecl
            | 'type ' ID tType                                                                                                    # SessionTypeDecl
            | 'type ' ID linearType '=' value                                                                                     # LTypeDeclAndAssign
            | 'type ' ID tType '=' value                                                                                          # STypeDeclAndAssign
            ;

daLineEnd   : ',' declAssign                                                                                                      # NextDeclaration
            | ';' process                                                                                                         # StartProcesses
            ;

/** Processes */

process	   : '0'                                                                                                                 # Termination
            /** Send and Receive can have one or more payloads */
            | 'send(' channel=value (',' payload+=value)+ ').' process                                                            # Output
            | 'receive(' channel=value (',' payload+=value)+ ').' process                                                         # Input
            | process '|' process                                                                                                 # Composition
            | '(new ' value ')' process                                                                                           # ChannelRestriction
            /** Case and Branching must give two or more options, hence '(...)+ ...' structure */
            /** Below rules are for linear pi Calculus */
            | 'case ' case=value ' of {' (option+=value '>' cont+=process ',')+ option+=value '>' cont+=process '}'               # Case
            /** Below rules are for session pi calculus */
            | '(new ' endpoint+=value endpoint+=value ')' process                                                                 # SessionRestriction
            | 'branch(' channel=value '){' (option+=value ':' cont+=process ',')+ option+=value ':' cont+=process '}'             # Branching
            | 'select(' channel=value ',' selection=value ').' process                                                            # Selection
            ;

value       : '*'                                                                                                                 # UnitValue
            | ID                                                                                                                  # Name
            | ID '_' value                                                                                                        # VariantValue
            | stringVal                                                                                                           # StringValue
            | intVal                                                                                                              # IntegerValue
            | booleanVal                                                                                                          # BooleanValue
            ;

/** Types */

linearType  : 'lo['linearType (',' linearType)? ']'                                                                               # LinearOutput
            | 'li['linearType (',' linearType)? ']'                                                                               # LinearInput
            | 'l#['linearType (',' linearType)? ']'                                                                               # LinearConnection
            | '#['linearType (',' linearType)? ']'                                                                                # Connection
            | '/[]'                                                                                                               # NoCapability
            | '<' (ID '_' linearType ',')+ ID '_' linearType '>'                                                                  # VariantValue
            | 'Unit'                                                                                                              # UnitValueLin
            | 'Bool'                                                                                                              # BooleanLin
            | 'Int'                                                                                                               # IntegerLin
            | 'String'                                                                                                            # StringLin
            ;

tType       : sType                                                                                                               # SessionType
            | '#'tType                                                                                                            # ChannelType
            | 'Unit'                                                                                                              # UnitValueSes
            | 'Bool'                                                                                                              # BooleanSes
            | 'Int'                                                                                                               # IntegerSes
            | 'String'                                                                                                            # StringSes
            ;

sType       : 'end'                                                                                                               # Termination
            | '?('tType(',' tType)? ').'sType                                                                                     # Receive
            | '!('tType(',' tType)? ').'sType                                                                                     # Send
            | '&{' (ID ':' sType ',')+ ID ':' sType '}'                                                                           # Branch
            | '+{' (ID ':' sType ',')+ ID ':' sType '}'                                                                           # Select
            ;

/** Tokens */

StringVal   : '"'AlphNum+'"' ;
IntVal      : Digit+ ;
BooleanVal  : 'True'
            | 'False'
            ;

fragment
AlphNum     : Char
            | Digit
fragment
Char        : 'A'..'Z'
            | 'a'..'z'
            ;
fragment
Digit       : '0'..'9' ;

ID          : NameStartChar NameChar* ;

fragment
NameChar
            : NameStartChar
            | '0'..'9'
            | '\u00B7'
            | '\u0300'..'\u036F'
            | '\u203F'..'\u2040'
            ;
fragment
NameStartChar
            : 'A'..'Z' | 'a'..'z'
            | '\u00C0'..'\u00D6'
            | '\u00D8'..'\u00F6'
            | '\u00F8'..'\u02FF'
            | '\u0370'..'\u037D'
            | '\u037F'..'\u1FFF'
            | '\u200C'..'\u200D'
            | '\u2070'..'\u218F'
            | '\u2C00'..'\u2FEF'
            | '\u3001'..'\uD7FF'
            | '\uF900'..'\uFDCF'
            | '\uFDF0'..'\uFFFD'
            ;

WS    : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines