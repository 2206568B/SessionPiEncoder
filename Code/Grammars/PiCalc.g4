grammar PiCalc;

encInput    : decls? processPrim                                                                                                      # DeclAndProcs
            ;

/** Declarations and Assignments */

decls       : decs+=declAssign (',' decs+=declAssign)*;

declAssign  : var=ID '=' value                                                                                                        # VariableAssignment
            | name=ID '(' value ':' typeName=ID ') :=' processPrim                                                                    # ProcessNamingNmd 
            | name=ID '(' value ':' tType ') :=' processPrim                                                                          # ProcessNamingSes
            | name=ID '(' value ':' linearType ') :=' processPrim                                                                     # ProcessNamingLin
            | 'type ' name=ID ':=' tType                                                                                              # SessionTypeNaming
            | 'type ' name=ID ':=' linearType                                                                                         # LinearTypeNaming
            | 'type ' var=ID basicType                                                                                                # BasicTypeDecl
            | 'type ' var=ID basicType '=' value                                                                                      # BasTypeDeclAndAssign
            | 'type ' var=ID typeName=ID                                                                                              # NamedTypeDecl
            | 'type ' var=ID typeName=ID '=' value                                                                                    # NmdTypeDeclAndAssign
            | 'type ' var=ID tType                                                                                                    # SessionTypeDecl
            | 'type ' var=ID tType '=' value                                                                                          # SesTypeDeclAndAssign
            | 'type ' var=ID linearType                                                                                               # LinearTypeDecl
            | 'type ' var=ID linearType '=' value                                                                                     # LinTypeDeclAndAssign
            ;

/** Processes */

processPrim : processSec                                                                                                              # SecondaryProc
            | '(' processPrim '|' processPrim ')'                                                                                     # Composition
            ;

processSec  : name=ID '(' value ')'                                                                                                   # NamedProcess
            | '0'                                                                                                                     # Termination
            /** Send and Receive can have multiple payloads in linear pi calculus */
            | 'send(' channel=value (',' payload+=value)+ ').' processSec                                                             # Output
            | '(new ' value ':' typeName=ID ') (' processPrim ')'                                                                     # ChannelRestrictionNmd
            /** Input and Channel Restriction must be duplicated due to type annotations needing to allow both linear and session types
            /** Case and Branching must give two or more options, hence '(...)+ ...' structure */
            /** Below rules are for session pi calculus */
            | '(new ' endpoint+=value endpoint+=value ':' sType ') (' processPrim ')'                                                 # SessionRestriction
            | '(new ' value ':' tType ') (' processPrim ')'                                                                           # ChannelRestrictionSes
            | 'receive(' channel=value ',' payload=value ':' plType=tType ').' processSec                                             # InputSes
            | 'branch(' channel=value '){' (option+=value ':' cont+=processSec ',')+ option+=value ':' cont+=processSec'}'            # Branching
            | 'select(' channel=value ',' selection=value ').' processSec                                                             # Selection
            /** Below rules are for linear pi Calculus */
            | '(new ' value ':' linearType ') (' processPrim ')'                                                                      # ChannelRestrictionLin
            | 'receive(' channel=value (',' payload+=value ':' plType+=linearType )+ ').' processSec                                  # InputLin
            | 'case ' case=value ' of {' (option+=variantVal '>' cont+=processSec ',')+ option+=variantVal '>' cont+=processSec'}'    # Case
            | 'send(' channel=value (',' payload+=value ':' plType+=linearType)+ ').' processSec                                      # OutputVariants
            ;

value       : '*'                                                                                                                     # UnitValue
            | ID                                                                                                                      # NamedValue
            | variantVal                                                                                                              # VariantValue
            | StringVal                                                                                                               # StringValue
            | IntVal                                                                                                                  # IntegerValue
            | BooleanVal                                                                                                              # BooleanValue
            ;

variantVal  : ID '_' value
            | ID '_(' value ':' linearType ')'
            ;

/** Types */

basicType   : 'Unit'                                                                                                              # UnitType
            | 'Bool'                                                                                                              # Boolean
            | 'Int'                                                                                                               # Integer
            | 'String'                                                                                                            # String
            ;

linearType  : name=ID                                                                                                             # NamedLinType
            | 'lo['(payload+=linearType ',')* payload+=linearType ']'                                                             # LinearOutput
            | 'li['(payload+=linearType ',')* payload+=linearType']'                                                              # LinearInput
            | 'l#['(payload+=linearType ',')* payload+=linearType']'                                                              # LinearConnection
            | '#['(payload+=linearType ',')* payload+=linearType']'                                                               # Connection
            | 'empty[]'                                                                                                           # NoCapability
            | '<' (variant+=ID '_' cont+=linearType ',')+ variant+=ID '_' cont+=linearType '>'                                    # VariantType
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