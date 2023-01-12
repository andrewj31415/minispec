# Generated from /home/andrewj31415/minispec/visual/MinispecPython.g4 by ANTLR 4.7.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .MinispecPythonParser import MinispecPythonParser
else:
    from MinispecPythonParser import MinispecPythonParser

# This class defines a complete generic visitor for a parse tree produced by MinispecPythonParser.

class MinispecPythonVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by MinispecPythonParser#lowerCaseIdentifier.
    def visitLowerCaseIdentifier(self, ctx:MinispecPythonParser.LowerCaseIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#upperCaseIdentifier.
    def visitUpperCaseIdentifier(self, ctx:MinispecPythonParser.UpperCaseIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#identifier.
    def visitIdentifier(self, ctx:MinispecPythonParser.IdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#anyIdentifier.
    def visitAnyIdentifier(self, ctx:MinispecPythonParser.AnyIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#arg.
    def visitArg(self, ctx:MinispecPythonParser.ArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#args.
    def visitArgs(self, ctx:MinispecPythonParser.ArgsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#argFormal.
    def visitArgFormal(self, ctx:MinispecPythonParser.ArgFormalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#argFormals.
    def visitArgFormals(self, ctx:MinispecPythonParser.ArgFormalsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#param.
    def visitParam(self, ctx:MinispecPythonParser.ParamContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#params.
    def visitParams(self, ctx:MinispecPythonParser.ParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#paramFormal.
    def visitParamFormal(self, ctx:MinispecPythonParser.ParamFormalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#paramFormals.
    def visitParamFormals(self, ctx:MinispecPythonParser.ParamFormalsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeName.
    def visitTypeName(self, ctx:MinispecPythonParser.TypeNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#packageDef.
    def visitPackageDef(self, ctx:MinispecPythonParser.PackageDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#packageStmt.
    def visitPackageStmt(self, ctx:MinispecPythonParser.PackageStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#importDecl.
    def visitImportDecl(self, ctx:MinispecPythonParser.ImportDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#bsvImportDecl.
    def visitBsvImportDecl(self, ctx:MinispecPythonParser.BsvImportDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeDecl.
    def visitTypeDecl(self, ctx:MinispecPythonParser.TypeDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeDefSynonym.
    def visitTypeDefSynonym(self, ctx:MinispecPythonParser.TypeDefSynonymContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeId.
    def visitTypeId(self, ctx:MinispecPythonParser.TypeIdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeDefEnum.
    def visitTypeDefEnum(self, ctx:MinispecPythonParser.TypeDefEnumContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeDefEnumElement.
    def visitTypeDefEnumElement(self, ctx:MinispecPythonParser.TypeDefEnumElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#typeDefStruct.
    def visitTypeDefStruct(self, ctx:MinispecPythonParser.TypeDefStructContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#structMember.
    def visitStructMember(self, ctx:MinispecPythonParser.StructMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#varBinding.
    def visitVarBinding(self, ctx:MinispecPythonParser.VarBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#letBinding.
    def visitLetBinding(self, ctx:MinispecPythonParser.LetBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#varInit.
    def visitVarInit(self, ctx:MinispecPythonParser.VarInitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#moduleDef.
    def visitModuleDef(self, ctx:MinispecPythonParser.ModuleDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#moduleId.
    def visitModuleId(self, ctx:MinispecPythonParser.ModuleIdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#moduleStmt.
    def visitModuleStmt(self, ctx:MinispecPythonParser.ModuleStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#submoduleDecl.
    def visitSubmoduleDecl(self, ctx:MinispecPythonParser.SubmoduleDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#inputDef.
    def visitInputDef(self, ctx:MinispecPythonParser.InputDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#methodDef.
    def visitMethodDef(self, ctx:MinispecPythonParser.MethodDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#ruleDef.
    def visitRuleDef(self, ctx:MinispecPythonParser.RuleDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#functionDef.
    def visitFunctionDef(self, ctx:MinispecPythonParser.FunctionDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#functionId.
    def visitFunctionId(self, ctx:MinispecPythonParser.FunctionIdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#varAssign.
    def visitVarAssign(self, ctx:MinispecPythonParser.VarAssignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#memberLvalue.
    def visitMemberLvalue(self, ctx:MinispecPythonParser.MemberLvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#indexLvalue.
    def visitIndexLvalue(self, ctx:MinispecPythonParser.IndexLvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#simpleLvalue.
    def visitSimpleLvalue(self, ctx:MinispecPythonParser.SimpleLvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#sliceLvalue.
    def visitSliceLvalue(self, ctx:MinispecPythonParser.SliceLvalueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#operatorExpr.
    def visitOperatorExpr(self, ctx:MinispecPythonParser.OperatorExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#condExpr.
    def visitCondExpr(self, ctx:MinispecPythonParser.CondExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#caseExpr.
    def visitCaseExpr(self, ctx:MinispecPythonParser.CaseExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#caseExprItem.
    def visitCaseExprItem(self, ctx:MinispecPythonParser.CaseExprItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#binopExpr.
    def visitBinopExpr(self, ctx:MinispecPythonParser.BinopExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#unopExpr.
    def visitUnopExpr(self, ctx:MinispecPythonParser.UnopExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#varExpr.
    def visitVarExpr(self, ctx:MinispecPythonParser.VarExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#bitConcat.
    def visitBitConcat(self, ctx:MinispecPythonParser.BitConcatContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#stringLiteral.
    def visitStringLiteral(self, ctx:MinispecPythonParser.StringLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#intLiteral.
    def visitIntLiteral(self, ctx:MinispecPythonParser.IntLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#returnExpr.
    def visitReturnExpr(self, ctx:MinispecPythonParser.ReturnExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#structExpr.
    def visitStructExpr(self, ctx:MinispecPythonParser.StructExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#undefinedExpr.
    def visitUndefinedExpr(self, ctx:MinispecPythonParser.UndefinedExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#sliceExpr.
    def visitSliceExpr(self, ctx:MinispecPythonParser.SliceExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#callExpr.
    def visitCallExpr(self, ctx:MinispecPythonParser.CallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#fieldExpr.
    def visitFieldExpr(self, ctx:MinispecPythonParser.FieldExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#parenExpr.
    def visitParenExpr(self, ctx:MinispecPythonParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#memberBinds.
    def visitMemberBinds(self, ctx:MinispecPythonParser.MemberBindsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#memberBind.
    def visitMemberBind(self, ctx:MinispecPythonParser.MemberBindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#beginEndBlock.
    def visitBeginEndBlock(self, ctx:MinispecPythonParser.BeginEndBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#regWrite.
    def visitRegWrite(self, ctx:MinispecPythonParser.RegWriteContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#stmt.
    def visitStmt(self, ctx:MinispecPythonParser.StmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#ifStmt.
    def visitIfStmt(self, ctx:MinispecPythonParser.IfStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#caseStmt.
    def visitCaseStmt(self, ctx:MinispecPythonParser.CaseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#caseStmtItem.
    def visitCaseStmtItem(self, ctx:MinispecPythonParser.CaseStmtItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#caseStmtDefaultItem.
    def visitCaseStmtDefaultItem(self, ctx:MinispecPythonParser.CaseStmtDefaultItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MinispecPythonParser#forStmt.
    def visitForStmt(self, ctx:MinispecPythonParser.ForStmtContext):
        return self.visitChildren(ctx)



del MinispecPythonParser