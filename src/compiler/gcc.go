package gcc

import "strings"

type UnsupportedCompilationMode struct {
	msg string
}

type GccWrapper struct {
	args              []string
	compiler          string
	srcfile           string
	objfile           string
	preprocessed_file string
}

func (gcc *GccWrapper) CanHandleCommand(args []string) (err error) {
	err = nil
	source_count := 0
	is_object_compilation := false
	has_object_file := false
	skip_next_arg := false
	gcc.compiler = args[0]
	for n, arg := range args {
		if skip_next_arg {
			skip_next_arg = false
			continue
		}
		if arg == "-c" {
			is_object_compilation = true
		} else if arg == "-x" {
			skip_next_arg = true
		} else if gcc.is_source_file(arg) {
			source_count += 1
			gcc.srcfile = arg
		} else if arg == "-o" {
			skip_next_arg = true
			if n < len(args) {
				gcc.objfile = args[n+1]
				has_object_file = true
			}
		}
	}
	if source_count == 0 {
		err = &UnsupportedCompilationMode{"no source files"}
	} else if source_count > 1 {
		err = &UnsupportedCompilationMode{"multiple sources"}
	} else if !is_object_compilation {
		err = &UnsupportedCompilationMode{"linking"}
	} else if !has_object_file {
		err = &UnsupportedCompilationMode{"output object is not specified"}
	}
	if err == nil {
		gcc.args = args
	}
	return err
}

func (gcc *GccWrapper) is_source_file(path string) bool {
	s := strings.Split(path, ".")
	if len(s) <= 1 {
		return false
	}
	fileext := s[len(s)-1]
	suffixes := []string{"c", "cxx", "cpp", "cc", "ii", "i"}
	for _, suffix := range suffixes {
		if suffix == fileext {
			return true
		}
	}
	return false
}

func (e *UnsupportedCompilationMode) Error() string {
	return e.msg
}
