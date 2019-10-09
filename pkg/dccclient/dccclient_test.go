package dccclient

import (
	"bytes"
	"github.com/asheplyakov/pdistcc/pkg/testhelpers"
	"strings"
	"testing"
)

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

func TestDccRequestBrokenDoti(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	var wsock bytes.Buffer
	c.wsock = &wsock
	c.doti = new(testhelpers.FaultyReader)
	c.dotilen = 100
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := c.Request(args)
	if err == nil {
		t.Errorf("TestDccRequestBrokenDoti unexpectedly passed")
	}
}

func TestDccRequestShortWriteDIST(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.wsock = testhelpers.NewLimitedWriter(11) // not enough even for one token
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := c.Request(args)
	if err == nil {
		t.Errorf("TestDccRequestShortWriteDIST unexpectedly passed")
	}
}

func TestDccRequestShortWriteARGC(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.wsock = testhelpers.NewLimitedWriter(20) // enough for one token only
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := c.Request(args)
	if err == nil {
		t.Errorf("TestDccRequestShortWriteARGC unexpectedly passed")
	}
}

func TestDccRequestShortWriteARGV(t *testing.T) {
	c := new(DccClient)
	c.version = 1
	c.wsock = testhelpers.NewLimitedWriter(36) // enough for 3 tokens only
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	err := c.Request(args)
	if err == nil {
		t.Errorf("TestDccRequestShortWriteARGV unexpectedly passed")
	}
}

func TestDccRequestShortWriteDOTI(t *testing.T) {
	args := []string{"gcc", "-c", "-o", "foo.o", "foo.c"}
	needBytes := 2*12 /* DIST + ARGC */ + len(args)*12 /* ARGV */ + len(strings.Join(args, "")) + 12 /* DOTI */

	c := new(DccClient)
	c.version = 1
	c.wsock = testhelpers.NewLimitedWriter(needBytes - 1) // enough for 3 tokens only
	err := c.Request(args)
	if err == nil {
		t.Errorf("TestDccRequestShortWriteARGV unexpectedly passed")
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
