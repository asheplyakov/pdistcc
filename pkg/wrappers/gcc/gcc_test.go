package gcc

import (
	e_wrappers "github.com/asheplyakov/pdistcc/pkg/wrappers/errors"
	"reflect"
	"testing"
)

func TestObjCompilationAccepted(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err != nil {
		t.Errorf("CanHandleCommand(%v) = %v, expected nil", cmd, err)
	}
}

func TestSourceFileC(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err != nil {
		t.Errorf("Unable to handle command %v", cmd)
	}
	if wrapper.srcfile != "foo.c" {
		t.Errorf("Wrong source file: %v, expected: %v", wrapper.srcfile, "foo.c")
	}
	if wrapper.lang() != "c" {
		t.Errorf("Wrong source language: %v, expected %v", wrapper.lang(), "c")
	}
}

func TestX(t *testing.T) {
	var wrapper GccWrapper
	cmd := []string{"gcc", "-c", "-o", "foo.o", "-x", "c", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err != nil {
		t.Errorf("Unabled to handle command %v", cmd)
	}
}

func TestManySources(t *testing.T) {
	var wrapper GccWrapper
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c", "bar.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err == nil {
		t.Errorf("Compilation of multiple sources is erroneously accepted")
		return
	}
	switch err.(type) {
	case *e_wrappers.UnsupportedCompilationMode:
		return
	default:
		t.Errorf("Unexpected error %v", err)
	}
}

func TestNoSources(t *testing.T) {
	var wrapper GccWrapper
	cmd := []string{"gcc", "-c", "-o", "foo.o"}
	err := wrapper.CanHandleCommand(cmd)
	if err == nil {
		t.Errorf("Compilation without sources is erroneously accepted")
		return
	}
	switch err.(type) {
	case *e_wrappers.UnsupportedCompilationMode:
		return
	default:
		t.Errorf("Unexpected error: %v", err)
	}
}

func TestLinkingRejected(t *testing.T) {
	var wrapper GccWrapper
	cmd := []string{"gcc", "-o", "foo", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err == nil {
		t.Errorf("Linking has been erroneously accepted")
		return
	}
	switch err.(type) {
	case *e_wrappers.UnsupportedCompilationMode:
		return
	default:
		t.Errorf("Unexpected error: %v", err)
	}
}

func TestNoObjectFileRejected(t *testing.T) {
	var wrapper GccWrapper
	cmd := []string{"gcc", "-c", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err == nil {
		t.Errorf("Linking has been erroneously accepted")
		return
	}
	switch err.(type) {
	case *e_wrappers.UnsupportedCompilationMode:
		return
	default:
		t.Errorf("Unexpected error: %v", err)
	}
}

func TestIsSourceFile(t *testing.T) {
	var wrapper GccWrapper
	srcFiles := []string{"foo.c", "foo.cc", "foo.cxx", "foo.cpp"}
	for _, name := range srcFiles {
		if !wrapper.is_source_file(name) {
			t.Errorf("TestIsSourceFile: file %s is not recognized as a source", name)
		}
	}
}

func TestIsNotSourceFile(t *testing.T) {
	var wrapper GccWrapper
	files := []string{"foo.h", "foo.txt", "foo.hpp"}
	for _, name := range files {
		if wrapper.is_source_file(name) {
			t.Errorf("TestIsNotSourceFile: file %s has been erroneously recognized as source", name)
		}
	}
}

func TestPreprocessorCmd(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err != nil {
		t.Errorf("Can't handle %v", cmd)
	}
	preprocessor_cmd, err := wrapper.PreprocessorCmd()
	expected := []string{"gcc", "-E", "-o", "foo.i", "foo.c"}
	if !reflect.DeepEqual(preprocessor_cmd, expected) {
		t.Errorf("PreprocessorCmd: expected %v, actual %v", expected, preprocessor_cmd)
	}
}

func TestMatchCompilerGXX(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"g++", "-c", "-o", "foo.o", "foo.cpp"}
	if ok := wrapper.MatchCompiler(cmd); !ok {
		t.Errorf("GccWrapper rejects command %v", cmd)
	}
}

func TestMatchCompilerGCCN(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"gcc-8", "-c", "-o", "foo.o", "foo.c"}
	if ok := wrapper.MatchCompiler(cmd); !ok {
		t.Errorf("GccWrapper rejects command %v", cmd)
	}
}

func TestMatchCompilerBarf(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"barf", "foo", "blah"}
	if ok := wrapper.MatchCompiler(cmd); ok {
		t.Errorf("GccWrapper erroneously accepted command %v", cmd)
	}
}
