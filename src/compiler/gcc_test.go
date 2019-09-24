package gcc

import "testing"

func TestObjCompilation(t *testing.T) {
	wrapper := GccWrapper{}
	cmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := wrapper.CanHandleCommand(cmd)
	if err != nil {
		t.Errorf("CanHandleCommand(%v) = %v, expected nil", cmd, err)
	}
}
