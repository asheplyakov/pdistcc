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

func TestDccProcessResponseJunk(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.rsock = bytes.NewBuffer([]byte("RandomJunkHere"))
	if _, err := c.HandleResponse(); err == nil {
		t.Errorf("unexpectedly accepted random junk as response")
	}
}
