package client

import (
	"bytes"
	"strings"
	"testing"
)

func TestDccEncode(t *testing.T) {
	encoded := DccEncode("OOPS", 31)
	expected := "OOPS0000001f"
	if encoded != expected {
		t.Errorf("DccEncode: expected %v, actual %v", expected, encoded)
	}
}

func TestDccEncodeString(t *testing.T) {
	arg := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	expected := "ARGV0000001f" + arg
	encoded := DccEncodeString("ARGV", arg)
	if encoded != expected {
		t.Errorf("DccEncodeString: expected %v, actual %v", expected, encoded)
	}
}

func TestDccRequest(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	var wsock bytes.Buffer
	c.wsock = &wsock
	c.doti = bytes.NewBuffer([]byte("0xdeadbeaf"))
	c.dotilen = 10
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := c.Request(args)
	if err != nil {
		t.Errorf("Unable to send command")
	}
	expected := []string{
		"DIST", "00000001",
		"ARGC", "00000005",
		"ARGV", "00000003", "gcc",
		"ARGV", "00000002", "-c",
		"ARGV", "00000002", "-o",
		"ARGV", "00000005", "foo.o",
		"ARGV", "00000005", "foo.c",
		"DOTI", "0000000a", "0xdeadbeaf",
	}
	if wsock.String() != strings.Join(expected, "") {
		t.Errorf(`DccClient.Request: expected: "%s", actual "%s"`, expected, wsock.String())
	}
}

func TestReadToken(t *testing.T) {
	sock := bytes.NewBuffer([]byte("DONE00000001"))
	val, err := readToken(sock, "DONE")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if val != 1 {
		t.Errorf("wrong value: expected: %d, actual: %d", 1, val)
	}
}

