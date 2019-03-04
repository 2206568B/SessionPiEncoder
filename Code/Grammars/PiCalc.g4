grammar PiCalc;

encInput    : decls? processPrim                                                                                                      # DeclAndProcs
            ;

/** Declarations and Assignments */

decls       : decs+=declAssign (',' decs+=declAssign)*;

declAssign  : var=ID '=' value                                                                                                        # VariableAssignment
            | name=ID '(' value ':' namedType ') :=' processPrim                                                                      # ProcessNamingNmd 
            | name=ID '(' value ':' tType ') :=' processPrim                                                                          # ProcessNamingSes
            | name=ID '(' value ':' linearType ') :=' processPrim                                                                     # ProcessNamingLin
            | 'type ' name=ID ':=' tType                                                                                              # SessionTypeNaming
            | 'type ' name=ID ':=' linearType                                                                                         # LinearTypeNaming
            | 'type ' var=ID namedType                                                                                                # NamedTypeDecl
            | 'type ' var=ID namedType '=' value                                                                                      # NmdTypeDeclAndAssign
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
            | 'end'                                                                                                                   # Termination
            /** Send and Receive can have multiple payloads in linear pi calculus */
            | 'send(' channel=value (',' payloads+=value)+ ').' processSec                                                            # Output
            | '(new ' value ':' namedType ') (' processPrim ')'                                                                       # ChannelRestrictionNmd
            /** Input and Channel Restriction must be duplicated due to type annotations needing to allow both linear and session types
            /** Case and Branching must give two or more options, hence '(...)+ ...' structure */
            /** Below rules are for session pi calculus */
            | '(new ' endpoint+=value endpoint+=value ':' sType ') (' processPrim ')'                                                 # SessionRestriction
            | '(new ' value ':' tType ') (' processPrim ')'                                                                           # ChannelRestrictionSes
            | 'receive(' channel=value ',' payload=value ':' plType=tType ').' processSec                                             # InputSes
            | 'branch(' channel=value '){' (opts+=value ':' conts+=processSec ',')+ opts+=value ':' conts+=processSec'}'              # Branching
            | 'select(' channel=value ',' selection=value ').' processSec                                                             # Selection
            /** Below rules are for linear pi Calculus */
            | '(new ' value ':' linearType ') (' processPrim ')'                                                                      # ChannelRestrictionLin
            | 'receive(' channel=value (',' payloads+=value ':' plTypes+=linearType )+ ').' processSec                                # InputLin
            | 'case ' case=value ' of {' (opts+=variantVal '>' conts+=processSec ',')+ opts+=variantVal '>' conts+=processSec'}'      # Case
            | 'send(' channel=value (',' payloads+=variantVal ':' plTypes+=linearType)+ ').' processSec                               # OutputVariants
            ;

value       : '*'                                                                                                                     # UnitValue
            | ID                                                                                                                      # NamedValue
            | '(' expression ')'                                                                                                      # ExprValue
            | StringVal                                                                                                               # StringValue
            | IntVal                                                                                                                  # IntegerValue
            | BooleanVal                                                                                                              # BooleanValue
            | variantVal                                                                                                              # VariantValue
            ;

expression  : value '==' value                                                                                                        # Eql
            | value '!=' value                                                                                                        # InEql
            | value '+' value                                                                                                         # IntAdd
            | value '-' value                                                                                                         # IntSub
            | value '*' value                                                                                                         # IntMult
            | value '/' value                                                                                                         # IntDiv
            | value '%' value                                                                                                         # IntMod
            | value '>' value                                                                                                         # IntGT
            | value '>=' value                                                                                                        # IntGTEq
            | value '<' value                                                                                                         # IntLT
            | value '<=' value                                                                                                        # IntLTEq
            | value '++' value                                                                                                        # StrConcat
            | 'NOT ' value                                                                                                            # BoolNot
            | value ' AND ' value                                                                                                     # BoolAnd
            | value ' OR ' value                                                                                                      # BoolOr
            | value ' XOR ' value                                                                                                     # BoolXor
            ;

variantVal  : ID '_' value
            | ID '_(' value ':' linearType ')'
            ;

/** Types */

basicLType  : 'lUnit'                                                                                                                 # LUnitType
            | 'lBool'                                                                                                                 # LBoolean
            | 'lInt'                                                                                                                  # LInteger
            | 'lString'                                                                                                               # LString
            ;

basicSType  : 'sUnit'                                                                                                                 # SUnitType
            | 'sBool'                                                                                                                 # SBoolean
            | 'sInt'                                                                                                                  # SInteger
            | 'sString'                                                                                                               # SString
            ;

namedType   : ID
            ;

linearType  : namedType                                                                                                               # NamedLinType
            | 'lo['(payloads+=linearType ',')* payloads+=linearType ']'                                                               # LinearOutput
            | 'li['(payloads+=linearType ',')* payloads+=linearType']'                                                                # LinearInput
            | 'l#['(payloads+=linearType ',')* payloads+=linearType']'                                                                # LinearConnection
            | '#['(payloads+=linearType ',')* payloads+=linearType']'                                                                 # Connection
            | 'empty[]'                                                                                                               # NoCapability
            | '<' (variants+=ID '_' conts+=linearType ',')+ variants+=ID '_' conts+=linearType '>'                                    # VariantType
            | basicLType                                                                                                              # BasicLinType
            ;

tType       : namedType                                                                                                               # NamedTType
            | sType                                                                                                                   # SessionType
            | ('#'tType | '#('tType')')                                                                                               # ChannelType
            | basicSType                                                                                                              # BasicSesType
            ;

sType       : namedType                                                                                                               # NamedSType
            | 'end'                                                                                                                   # Terminate
            | ('?'payload=tType'.'sType | '?('payload=tType').'sType )                                                                # Receive
            | ('!'payload=tType'.'sType | '!('payload=tType').'sType )                                                                # Send
            | '&{' (opts+=value ':' conts+=sType ',')+ opts+=value ':' conts+=sType '}'                                               # Branch
            | '+{' (opts+=value ':' conts+=sType ',')+ opts+=value ':' conts+=sType '}'                                               # Select
            ;

/** Tokens */

StringVal   : '"'AlphNum+'"' ;
IntVal      : '-'? Digit+ ;
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