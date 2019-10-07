package compiler

import (
	"testing"
)

func TestGetCompilerWrapperGCC(t *testing.T) {
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	wrapper := GetCompilerWrapper(cmd)
	if wrapper == nil {
		t.Errorf("failed to find a wrapper for %v", cmd)
	}
	if _, ok := wrapper.(*GccWrapper); !ok {
		t.Errorf("wrapper of %v is not GccWrapper", cmd)
	}
}

func TestGetCompilerWrapperGCCX(t *testing.T) {
	cmd := []string{"gcc-7", "-c", "-o", "foo.o", "foo.c"}
	wrapper := GetCompilerWrapper(cmd)
	if wrapper == nil {
		t.Errorf("failed to find a wrapper for %v", cmd)
	}
	if _, ok := wrapper.(*GccWrapper); !ok {
		t.Errorf("wrapper of %v is not GccWrapper", cmd)
	}
}

func TestGetCompilerWrapperGCCXY(t *testing.T) {
	cmd := []string{"gcc-7.4", "-c", "-o", "foo.o", "foo.c"}
	wrapper := GetCompilerWrapper(cmd)
	if wrapper == nil {
		t.Errorf("failed to find a wrapper for %v", cmd)
	}
	if _, ok := wrapper.(*GccWrapper); !ok {
		t.Errorf("wrapper of %v is not GccWrapper", cmd)
	}
}

func TestGetCompilerWrapperGCCAbsPath(t *testing.T) {
	cmd := []string{"/usr/bin/gcc-7.4", "-c", "-o", "foo.o", "foo.c"}
	wrapper := GetCompilerWrapper(cmd)
	if wrapper == nil {
		t.Errorf("failed to find a wrapper for %v", cmd)
	}
	if _, ok := wrapper.(*GccWrapper); !ok {
		t.Errorf("wrapper of %v is not GccWrapper", cmd)
	}
}

func TestGetCompilerWrapperNegative(t *testing.T) {
	cmd := []string{"foo", "bar", "bazz"}
	if wrapper := GetCompilerWrapper(cmd); wrapper != nil {
		t.Errorf("error: bogus command %v got a wrapper", cmd)
	}
}
