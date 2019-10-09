package dccproto

import (
	"bytes"
	"github.com/asheplyakov/pdistcc/pkg/testhelpers"
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

func TestSendTokenShortWrite(t *testing.T) {
	sock := testhelpers.NewLimitedWriter(1)
	err := SendToken(sock, "DIST", 1)
	if err == nil {
		t.Errorf("TestSendTokenShortWrite: unexpectedly passed")
	}
}

func TestSendTokenFailedWrite(t *testing.T) {
	var sock testhelpers.FaultyWriter
	err := SendToken(&sock, "DIST", 1)
	if err == nil {
		t.Errorf("TestSendTokenShortWrite: unexpectedly passed")
	}
}

func TestSendStringToken(t *testing.T) {
	var sock bytes.Buffer
	if err := SendStringToken(&sock, "ARGV", "-o"); err != nil {
		t.Errorf("TestSendStringToken: unexpected error: %v", err)
	}
	expected := "ARGV" + "00000002" + "-o"
	if sock.String() != expected {
		t.Errorf(`SendStringToken: expected: "%s", actual: "%s"`, expected, sock.String())
	}
}

func TestSendStringTokenFailedWrite(t *testing.T) {
	var sock testhelpers.FaultyWriter
	if err := SendStringToken(&sock, "ARGV", "-o"); err == nil {
		t.Errorf("TestSendStringTokenFailedWrite unexpectedly passed")
	}
}

func TestSendStringTokenShortWrite(t *testing.T) {
	sock := testhelpers.NewLimitedWriter(1)
	if err := SendStringToken(sock, "ARGV", "-o"); err == nil {
		t.Errorf("TestSendStringTokenShortWrite unexpectedly passed")
	}
}

func TestReadToken(t *testing.T) {
	sock := bytes.NewBuffer([]byte("DONE00000001"))
	val, err := ReadToken(sock, "DONE")
	if err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if val != 1 {
		t.Errorf("wrong value: expected: %d, actual: %d", 1, val)
	}
}

func TestReadTokenFailedRead(t *testing.T) {
	var sock testhelpers.FaultyReader
	_, err := ReadToken(&sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenFailedRead: unexpectedly passed")
	}
}

func TestReadTokenShortRead(t *testing.T) {
	var sock testhelpers.ShortReader
	_, err := ReadToken(&sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenShortRead uexpectedly passed")
	}
}

func TestReadTokenInvalidInt(t *testing.T) {
	sock := bytes.NewBuffer([]byte("DISTxxxyyyzz"))
	_, err := ReadToken(sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenInvalidInt unexpectedly passed")
	}
}

func TestReadTokenTo(t *testing.T) {
	var sink bytes.Buffer
	payload := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	sock := bytes.NewBuffer([]byte("DOTO" + "0000001f" + payload))
	if err := ReadTokenTo(sock, "DOTO", &sink); err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if sink.String() != payload {
		t.Errorf("wrong payload:\nexpected: %s\nactual:   %s", payload, sink.String())
	}
}

func TestReadTokenToFaultyWrite(t *testing.T) {
	var doto testhelpers.FaultyWriter
	sock := bytes.NewBuffer([]byte("DOTO" + "00000001" + "a"))
	if err := ReadTokenTo(sock, "DOTO", &doto); err == nil {
		t.Errorf("TestReadTokenToFaultyWrite unexpectedly passed")
	}
}
