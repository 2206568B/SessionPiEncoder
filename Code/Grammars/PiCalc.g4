grammar PiCalc;

encInput    : decls process                                                                                                       # DeclAndProcs
            ;

/** Declarations and Assignments */

decls       : decs+=declAssign (',' decs+=declAssign)*;

declAssign  : var=ID '=' value                                                                                                    # VariableAssignment
            | name=ID '(' value ':' tType ') :=' process                                                                          # ProcessNamingSes
            | name=ID '(' value ':' linearType ') :=' process                                                                     # ProcessNamingLin
            | 'type ' name=ID ':=' tType                                                                                          # SessionTypeNaming
            | 'type ' name=ID ':=' linearType                                                                                     # LinearTypeNaming
            | 'type ' var=ID tType                                                                                                # SessionTypeDecl
            | 'type ' var=ID tType '=' value                                                                                      # SesTypeDeclAndAssign
            | 'type ' var=ID linearType                                                                                           # LinearTypeDecl
            | 'type ' var=ID linearType '=' value                                                                                 # LinTypeDeclAndAssign
            ;

/** Processes */

process     : name=ID '(' value ')'                                                                                               # NamedProcess
            | '0'                                                                                                                 # Termination
            /** Send and Receive can have multiple payloads in linear pi calculus */
            | 'send(' channel=value (',' payload+=value)+ ').' process                                                            # Output
            | '(' process ')' '|' '(' process ')'                                                                                 # Composition
            /** Input and Channel Restriction must be duplicated due to type annotations needing to allow both linear and session types
            /** Case and Branching must give two or more options, hence '(...)+ ...' structure */
            /** Below rules are for session pi calculus */
            | '(new ' endpoint+=value endpoint+=value ':' sType ')' '(' process ')'                                               # SessionRestriction
            | '(new ' value ':' tType ')' '(' process ')'                                                                         # ChannelRestrictionSes
            | 'receive(' channel=value ',' payload=value ':' plType=tType ').' process                                            # InputSes
            | 'branch(' channel=value '){' (option+=value ':' cont+=process ',')+ option+=value ':' cont+=process '}'             # Branching
            | 'select(' channel=value ',' selection=value ').' process                                                            # Selection
            /** Below rules are for linear pi Calculus */
            | '(new ' value ':' linearType ')' '(' process ')'                                                                    # ChannelRestrictionLin
            | 'receive(' channel=value (',' payload+=value ':' plType+=linearType )+ ').' process                                 # InputLin
            | 'case ' case=value ' of {' (option+=value '>' cont+=process ',')+ option+=value '>' cont+=process '}'               # Case
            ;

value       : '*'                                                                                                                 # UnitValue
            | ID                                                                                                                  # Name
            | ID '_' value                                                                                                        # VariantValue
            | StringVal                                                                                                           # StringValue
            | IntVal                                                                                                              # IntegerValue
            | BooleanVal                                                                                                          # BooleanValue
            ;

/** Types */

basicType   : 'Unit'                                                                                                              # UnitType
            | 'Bool'                                                                                                              # Boolean
            | 'Int'                                                                                                               # Integer
            | 'String'                                                                                                            # String
            ;

linearType  : name=ID                                                                                                             # NamedLinType
            | 'lo['(payload+=linearType ',')* cont=linearType ']'                                                                 # LinearOutput
            | 'li['payload+=linearType (',' cont=linearType)* ']'                                                                 # LinearInput
            | 'l#['payload+=linearType (',' cont=linearType)* ']'                                                                 # LinearConnection
            | '#['payload+=linearType (',' cont=linearType)* ']'                                                                  # Connection
            | 'empty[]'                                                                                                           # NoCapability
            | '<' (ID '_' linearType ',')+ ID '_' linearType '>'                                                                  # VariantType
            | basicType                                                                                                           # BasicLinType
            ;

tType       : name=ID                                                                                                             # NamedTType
            | sType                                                                                                               # SessionType
            | '#'tType                                                                                                            # ChannelType
            | basicType                                                                                                           # BasicSesType
            ;

sType       : name=ID                                                                                                             # NamedSType
            | 'end'                                                                                                               # Terminate
            | '?'payload=tType'.'sType                                                                                            # Receive
            | '!'payload=tType'.'sType                                                                                            # Send
            | '&{' (option+=value ':' cont+=sType ',')+ option+=value ':' cont+=sType '}'                                         # Branch
            | '+{' (option+=value ':' cont+=sType ',')+ option+=value ':' cont+=sType '}'                                         # Select
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
            ;
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
            | '\u0027'
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