package gcc

import (
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
