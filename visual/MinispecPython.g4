/** $lic$
 * Copyright (C) 2019-2020 by Daniel Sanchez
 *
 * This file is part of the Minispec compiler and toolset.
 *
 * Minispec is free software; you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, version 2.
 *
 * Minispec is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see <http://www.gnu.org/licenses/>. 
 */

// Minispec ANTLRv4 grammar
// Author: Daniel Sanchez
// Nomenclature follows BSV reference manual; some elements are borrowed from
// https://github.com/cambridgehackers/bsvtokami/blob/master/src/main/antlr/bsvtokami/BSV.g4 

// The name of the grammar must match the name of the file.
grammar MinispecPython;

UpperCaseIdentifier : [A-Z][a-zA-Z0-9_]* ;
LowerCaseIdentifier : [a-z_][a-zA-Z0-9_]* ;
DollarIdentifier : [$][a-z][a-zA-Z0-9_$]* ;

lowerCaseIdentifier : LowerCaseIdentifier ;
upperCaseIdentifier : UpperCaseIdentifier ;
identifier : lowerCaseIdentifier | upperCaseIdentifier ;
anyIdentifier : lowerCaseIdentifier | upperCaseIdentifier | DollarIdentifier ;

// NOTE: This is now a precise regex (does not allow invalid int literals) and octal is not allowed
IntLiteral : ([0-9_]+) | (([1-9][0-9]*)?('\'h'[0-9a-fA-F_]+ | '\'d'[0-9_]+ | '\'b'[0-1_]+)) ;
StringLiteral : '"' (~ [\f\n\r\t"])* '"' ;

WhiteSpace : [ \f\n\r\t]+ -> channel (3) ;
OneLineComment   : '//' .*? '\r'? '\n' -> channel (3) ;
InlineComment : '/*' .*? '*/' -> channel (3) ;

// Uncomment to avoid lexer errors; this centralizes error handling in the
// parser, but it loses some error info (e.g., the error on unterminated
// strings is worse with this)
// ErrorToken: . ;

// Common syntax elements
arg: expression ;
args: '(' (arg (',' arg)*)? ')' ;
argFormal: typeName argName=lowerCaseIdentifier ;
argFormals: '(' (argFormal (',' argFormal)*)? ')' ;

param: typeName | intParam=expression ;
params: '#' '(' (param (',' param)*)? ')' ;
// To enable partial specialization, a paramFormal can be a param
// NOTE: type must be 'Integer', but can't use 'Integer' here because it gets
// picked up as a token by the lexer. We could pollute the upperCaseIdentifier
// def, but instead let's check that type == 'Integer' on static elaboration.
paramFormal: typeName intName=lowerCaseIdentifier | 'type' typeValue=upperCaseIdentifier | param ;
paramFormals: '#' '(' (paramFormal (',' paramFormal)*)? ')' ;

// type is a reserved python keyword, so we replace it with typeName.
// we rename the original typeName (used once, in paramFormal) to typeValue.
typeName: name=upperCaseIdentifier params? ;


packageDef : packageStmt* EOF ;
packageStmt : 
    importDecl
    | bsvImportDecl
    | typeDecl
    | varDecl
    | functionDef
    | moduleDef
    ;


importDecl : 'import' identifier (',' identifier)* ';' ;
bsvImportDecl: 'bsvimport' upperCaseIdentifier (',' upperCaseIdentifier)* ';' ;

typeDecl :
    typeDefSynonym
    | typeDefEnum
    | typeDefStruct
    ;

typeDefSynonym : 'typedef' typeName typeId ';' ;
typeId : name=upperCaseIdentifier paramFormals? ;

typeDefEnum : 'typedef' 'enum' '{' typeDefEnumElement (',' typeDefEnumElement)* '}' upperCaseIdentifier ';' ;
typeDefEnumElement : tag=upperCaseIdentifier ('=' tagval=IntLiteral)? ;

typeDefStruct : 'typedef' 'struct' '{' (structMember)* '}' typeId ';' ;
structMember : typeName lowerCaseIdentifier ';' ;

varDecl :
    typeName varInit (',' varInit)*  ';' #varBinding
    | 'let' (lowerCaseIdentifier | ('{' lowerCaseIdentifier (',' lowerCaseIdentifier )* '}'))  ('=' rhs=expression)? ';' #letBinding
    ;
varInit : var=lowerCaseIdentifier ('=' rhs=expression)? ;

moduleDef : 'module' moduleId argFormals? ';' moduleStmt* 'endmodule' ;
moduleId: name=upperCaseIdentifier paramFormals? ;
moduleStmt :
    submoduleDecl
    | inputDef 
    | methodDef
    | functionDef
    | ruleDef
    | stmt
    ;
submoduleDecl : typeName name=lowerCaseIdentifier args? ';' ;
inputDef : 'input' typeName name=lowerCaseIdentifier ('default' '=' defaultVal=expression)? ';' ;
// NOTE: For now, no parametric methods, as that would complicate codegen
methodDef : 'method' typeName name=lowerCaseIdentifier argFormals? (';' stmt* 'endmethod' | '=' expression ';') ;
ruleDef : 'rule' name=lowerCaseIdentifier ';' stmt* 'endrule' ;
functionDef : 'function' typeName functionId argFormals? (';' stmt* 'endfunction' | '=' expression ';') ;
functionId: name=lowerCaseIdentifier paramFormals? ;

// vars is a python built-in, so we rename vars to varList.
varAssign :
    var=lvalue '=' expression ';'
    | varList='{' lvalue (',' lvalue)* '}' '=' expression ';'
    ;
lvalue :
    lowerCaseIdentifier #simpleLvalue
    | lvalue '.' lowerCaseIdentifier #memberLvalue
    | lvalue indexLBracket='[' index=expression indexRBracket=']' #indexLvalue
    | lvalue sliceLBracket='[' msb=expression sliceColon=':' lsb=expression sliceRBracket=']' #sliceLvalue
    ;

expression :
    <assoc=right> pred=expression condQmark='?' expression condColon=':' expression #condExpr
    | 'case' '(' expression ')' caseExprItem* 'endcase' #caseExpr
    | binopExpr #operatorExpr
    ;
caseExprItem :
    ('default'
    | (exprPrimary (',' exprPrimary )* )) ':' body=expression ';'
    ;
binopExpr :
     left=binopExpr op='**' right=binopExpr
    | left=binopExpr op=('*' | '/' | '%') right=binopExpr
    | left=binopExpr op=('+' | '-') right=binopExpr
    | left=binopExpr op=('<<' | '>>') right=binopExpr
    | left=binopExpr op=('<' | '<=' | '>' | '>=') right=binopExpr
    | left=binopExpr op=('==' | '!=') right=binopExpr
    | left=binopExpr op=('&' | '^' | '^~' | '~^') right=binopExpr
    | left=binopExpr op='|' right=binopExpr
    | left=binopExpr op='&&' right=binopExpr
    | left=binopExpr op='||' right=binopExpr
    | unopExpr
    ;
unopExpr : 
     op=('!' | '~' | '&' | '~&' | '|' | '~|' | '^' | '^~' | '~^') exprPrimary
    | op=('+' | '-') exprPrimary
    | exprPrimary
    ;
exprPrimary :
    '(' expression ')' #parenExpr
    | exprPrimary '.' field=identifier #fieldExpr  // FIXME: shouldn't field be lowerCaseIdentifier?
    | var=anyIdentifier params? #varExpr
    | IntLiteral #intLiteral
    | StringLiteral #stringLiteral
    | '?' #undefinedExpr
    | 'return' expression #returnExpr
    | bitConcatOpen='{' expression (bitConcatComma+=',' expression)* bitConcatClose='}' #bitConcat
    | array=exprPrimary '[' msb=expression (':' lsb=expression)? ']' #sliceExpr
    | fcn=exprPrimary '(' (expression (',' expression)*)? ')' #callExpr
    | typeName '{' memberBinds '}' #structExpr
    ;
memberBinds : memberBind (',' memberBind)* ;
memberBind : field=lowerCaseIdentifier ':' expression ;
beginEndBlock : 'begin' stmt* 'end' ;
regWrite : lhs=lvalue '<=' rhs=expression ';' ;

stmt :
     varDecl
    | varAssign
    | regWrite
    | beginEndBlock
    | ifStmt
    | caseStmt
    | forStmt
    | exprPrimary ';'
    ;

ifStmt : 'if' '(' expression ')' stmt ('else' stmt)? ;

caseStmt : 'case' '(' expression ')' caseStmtItem* caseStmtDefaultItem? 'endcase' ;
caseStmtItem : expression (',' expression)* ':' stmt ;
caseStmtDefaultItem : 'default' ':' stmt ;

forStmt : 'for' '(' typeName initVar=lowerCaseIdentifier '=' expression ';' expression ';' updVar=lowerCaseIdentifier '=' expression ')' stmt ;
