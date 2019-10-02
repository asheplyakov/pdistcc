package client

import (
	"bytes"
	"errors"
	"strings"
	"testing"
)

type FaultyWriter int

func (w *FaultyWriter) Write(p []byte) (n int, err error) {
	return 0, errors.New("you should not pass")
}

type FaultyReader int

func (r *FaultyReader) Read(p []byte) (n int, err error) {
	return 0, errors.New("you should not pass")
}

type ShortWriter int

func (w *ShortWriter) Write(p []byte) (n int, err error) {
	return
}

type ShortReader int

func (r *ShortReader) Read(p []byte) (n int, err error) {
	if len(p) >= 1 {
		p[0] = 'a'
		n = 1
	}
	return
}

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
	var sock ShortWriter
	err := sendToken(&sock, "DIST", 1)
	if err == nil {
		t.Errorf("TestSendTokenShortWrite: unexpectedly passed")
	}
}

func TestSendTokenFailedWrite(t *testing.T) {
	var sock FaultyWriter
	err := sendToken(&sock, "DIST", 1)
	if err == nil {
		t.Errorf("TestSendTokenShortWrite: unexpectedly passed")
	}
}

func TestSendStringToken(t *testing.T) {
	var sock bytes.Buffer
	if err := sendStringToken(&sock, "ARGV", "-o"); err != nil {
		t.Errorf("TestSendStringToken: unexpected error: %v", err)
	}
	expected := "ARGV" + "00000002" + "-o"
	if sock.String() != expected {
		t.Errorf(`sendStringToken: expected: "%s", actual: "%s"`, expected, sock.String())
	}
}

func TestSendStringTokenFailedWrite(t *testing.T) {
	var sock FaultyWriter
	if err := sendStringToken(&sock, "ARGV", "-o"); err == nil {
		t.Errorf("TestSendStringTokenFailedWrite unexpectedly passed")
	}
}

func TestSendStringTokenShortWrite(t *testing.T) {
	var sock ShortWriter
	if err := sendStringToken(&sock, "ARGV", "-o"); err == nil {
		t.Errorf("TestSendStringTokenShortWrite unexpectedly passed")
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

func TestReadTokenFailedRead(t *testing.T) {
	var sock FaultyReader
	_, err := readToken(&sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenFailedRead: unexpectedly passed")
	}
}

func TestReadTokenShortRead(t *testing.T) {
	var sock ShortReader
	_, err := readToken(&sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenShortRead uexpectedly passed")
	}
}

func TestReadTokenInvalidInt(t *testing.T) {
	sock := bytes.NewBuffer([]byte("DISTxxxyyyzz"))
	_, err := readToken(sock, "DIST")
	if err == nil {
		t.Errorf("TestReadTokenInvalidInt unexpectedly passed")
	}
}

func TestReadTokenTo(t *testing.T) {
	var sink bytes.Buffer
	payload := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	sock := bytes.NewBuffer([]byte("DOTO" + "0000001f" + payload))
	if err := readTokenTo(sock, "DOTO", &sink); err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if sink.String() != payload {
		t.Errorf("wrong payload:\nexpected: %s\nactual:   %s", payload, sink.String())
	}
}

func TestReadTokenToFaultyWrite(t *testing.T) {
	var doto FaultyWriter
	sock := bytes.NewBuffer([]byte("DOTO" + "00000001" + "a"))
	if err := readTokenTo(sock, "DOTO", &doto); err == nil {
		t.Errorf("TestReadTokenToFaultyWrite unexpectedly passed")
	}
}

func TestDccProcessResponse(t *testing.T) {
	var (
		ofile bytes.Buffer
		sout  bytes.Buffer
		serr  bytes.Buffer
	)
	c := new(DccClient)
	c.version = 1
	response := strings.Join([]string{
		"DONE", "00000001",
		"STAT", "00000000",
		"SERR", "00000004", "serr",
		"SOUT", "00000004", "sout",
		"DOTO", "00000007", "fakeobj",
	}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	c.ofile = &ofile
	c.stdout = &sout
	c.stderr = &serr
	status, err := c.HandleResponse()
	if err != nil {
		t.Errorf("unexpected error %v", err)
	}
	if status != 0 {
		t.Errorf("wrong status: %d, expected: %d", status, 0)
	}
	if sout.String() != "sout" {
		t.Errorf("wrong stdout: %s, expected: %s", sout.String(), "sout")
	}
	if serr.String() != "serr" {
		t.Errorf("wrong stderr: %s, expected: %s", serr.String(), "serr")
	}
	if ofile.String() != "fakeobj" {
		t.Errorf(`DccClient.HandleResponse(): expected: "%s", actual "%s"`, "fakeobj", ofile.String())
	}
}

func TestDccProcessResponseWrongVersion(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	response := strings.Join([]string{"DONE", "0000000a"}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	_, err := c.HandleResponse()
	if err == nil {
		t.Errorf("Unexpectedly accepted protocol version %d", 10)
	}
}

func TestDccProcessResponseNoSTAT(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	response := strings.Join([]string{
		"DONE", "00000001",
		"SERR", "00000004", "serr",
		"SOUT", "00000004", "sout",
		"DOTO", "00000004", "fake",
	}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted response without STAT")
	}
}

func TestDccProcessResponseNoSERR(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.stdout = bytes.NewBuffer(nil)
	c.stderr = bytes.NewBuffer(nil)
	response := strings.Join([]string{
		"DONE", "00000001",
		"STAT", "00000000",
		"SOUT", "00000004", "sout",
		"DOTO", "00000004", "fake",
	}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted response without SERR")
	}
}

func TestDccProcessResponseNoSOUT(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.stdout = bytes.NewBuffer(nil)
	c.stderr = bytes.NewBuffer(nil)
	response := strings.Join([]string{
		"DONE", "00000001",
		"STAT", "00000000",
		"SERR", "00000004", "serr",
		"DOTO", "00000004", "fake",
	}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted response without SERR")
	}
}

func TestDccProcessResponseNoDOTO(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.stdout = bytes.NewBuffer(nil)
	c.stderr = bytes.NewBuffer(nil)
	c.ofile = bytes.NewBuffer(nil)
	response := strings.Join([]string{
		"DONE", "00000001",
		"STAT", "00000000",
		"SERR", "00000004", "serr",
		"SOUT", "00000004", "sout",
	}, "")
	c.rsock = bytes.NewBuffer([]byte(response))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted response without DOTO")
	}
}

func TestDccProcessResponseJunk(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.rsock = bytes.NewBuffer([]byte("RandomJunkHere"))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted random junk as response")
	}
}
