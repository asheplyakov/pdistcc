package server

import (
	"bytes"
	"reflect"
	"strings"
	"testing"

	_ "github.com/asheplyakov/pdistcc/pkg/testhelpers"
)

func TestDccServerReadRequest(t *testing.T) {
	s, err := NewDccServer()
	if err != nil {
		t.Errorf(`failed to create DccServer, error: "%v"`, err)
		return
	}
	var (
		doti bytes.Buffer
	)
	request := strings.Join([]string{
		"DIST", "00000001",
		"ARGC", "00000005",
		"ARGV", "00000003", "gcc",
		"ARGV", "00000002", "-c",
		"ARGV", "00000002", "-o",
		"ARGV", "00000005", "foo.o",
		"ARGV", "00000005", "foo.c",
		"DOTI", "00000004", "fake",
	}, "")
	s.rsock = bytes.NewBuffer([]byte(request))
	cmd, err := s.readRequest(&doti)
	if err != nil {
		t.Errorf("unexpected error %v", err)
	}
	expectedCmd := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	if !reflect.DeepEqual(cmd, expectedCmd) {
		t.Errorf(`wrong cmd: expected "%v", actual "%v"`, expectedCmd, cmd)
	}
	if doti.String() != "fake" {
		t.Errorf(`wrong doti: expected "fake", got "%s"`, doti.String())
	}

}
