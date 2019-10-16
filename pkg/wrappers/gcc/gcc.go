package gcc

import (
	"fmt"
	e_wrappers "github.com/asheplyakov/pdistcc/pkg/wrappers/errors"
	"path/filepath"
	"regexp"
	"strings"
)

type GccWrapper struct {
	args              []string
	compiler          string
	srcfile           string
	objfile           string
	preprocessed_file string
}

func (gcc *GccWrapper) MatchCompiler(args []string) bool {
	if len(args) < 1 {
		return false
	}
	matchers := []string{
		`\bgcc(-[3-9](\.[0-9]+)*)*$`,
		`\bg\+\+(-[3-9](\.[0-9]+)*)*$`,
	}
	compiler := args[0]
	for _, rx := range matchers {
		if match, _ := regexp.MatchString(rx, compiler); match {
			return true
		}
	}
	return false
}

func (gcc *GccWrapper) CanHandleCommand(args []string) (err error) {
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
		err = &e_wrappers.UnsupportedCompilationMode{"no source files"}
	} else if source_count > 1 {
		err = &e_wrappers.UnsupportedCompilationMode{"multiple sources"}
	} else if !is_object_compilation {
		err = &e_wrappers.UnsupportedCompilationMode{"linking"}
	} else if !has_object_file {
		err = &e_wrappers.UnsupportedCompilationMode{"output object is not specified"}
	}
	if err == nil {
		gcc.args = args
	}
	return err
}

func (gcc *GccWrapper) lang() string {
	ret := "c++"
	suffix := strings.ToLower(filepath.Ext(gcc.srcfile))
	if suffix == ".c" || suffix == ".i" {
		ret = "c"
	}
	return ret
}

func fileNameWithoutExtension(path string) string {
	return strings.TrimSuffix(path, filepath.Ext(path))
}

func (gcc *GccWrapper) preprocessed_filename(objfile string) string {
	doti_suffix := "ii"
	if gcc.lang() == "c" {
		doti_suffix = "i"
	}
	return fileNameWithoutExtension(objfile) + "." + doti_suffix
}

func (gcc *GccWrapper) PreprocessorCmd() ([]string, error) {
	var cmd []string
	cmd = append(cmd, gcc.compiler)
	next_arg_is_object := false
	for _, arg := range gcc.args[1:] {
		skip_arg := false
		if "-c" == arg {
			cmd = append(cmd, "-E")
			skip_arg = true
		} else if next_arg_is_object {
			gcc.objfile = arg
			gcc.preprocessed_file = gcc.preprocessed_filename(arg)
			cmd = append(cmd, gcc.preprocessed_file)
			next_arg_is_object = false
			skip_arg = true
		} else if "-o" == arg {
			next_arg_is_object = true
		}
		if !skip_arg {
			cmd = append(cmd, arg)
		}
	}
	return cmd, nil
}

func (gcc *GccWrapper) isPreprocessorArg(arg string) (skip bool, skip_next bool) {
	switch {
	case arg[:2] == "-I":
		skip = true
	case arg[:2] == "-D":
		skip = true
	}
	return
}

func (gcc *GccWrapper) CompilerCmd(doti, ofile string) (cmd []string, err error) {
	if len(gcc.args) == 0 || gcc.srcfile == "" || gcc.objfile == "" {
		err = fmt.Errorf("Should have called CanHandleCommand first")
		return
	}

	cmd = append(cmd, gcc.compiler)
	skip, skip_next := false, false
	for _, arg := range gcc.args[1:] {
		if skip_next {
			skip_next = false
			continue
		}
		if skip, skip_next = gcc.isPreprocessorArg(arg); skip {
			continue
		}
		switch {
		case arg == gcc.srcfile:
			cmd = append(cmd, "-x", gcc.lang(), doti)
		case arg == gcc.objfile:
			cmd = append(cmd, ofile)
		default:
			cmd = append(cmd, arg)
		}
	}
	return
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
