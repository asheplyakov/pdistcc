package compiler

type CompilerWrapper interface {
	MatchCompiler(args []string) bool
	CanHandleCommand(args []string) error
	PreprocessorCmd() ([]string, error)
	CompilerCmd() ([]string, error)
}

func GetCompilerWrapper(args []string) CompilerWrapper {
	wrappers := []CompilerWrapper{&GccWrapper{}}
	for _, wrapper := range wrappers {
		if matched := wrapper.MatchCompiler(args); matched {
			return wrapper
		}
	}
	return nil
}
