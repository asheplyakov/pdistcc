package client

import (
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"strconv"
)

const (
	TOKEN_LEN      int = 12
	TOKEN_NAME_LEN int = 4
)

type DccClient struct {
	version int
	rsock   io.Reader
	wsock   io.Writer
	stdout  io.Writer
	stderr  io.Writer
	doti    io.Reader
	dotilen int
	ofile   io.Writer
}

func DccEncode(token string, val int) string {
	var tok [4]byte
	copy(tok[:], token)
	return fmt.Sprintf("%s%08x", string(tok[:]), val)
}

func DccEncodeString(token string, val string) string {
	var tok [4]byte
	copy(tok[:], token)
	return fmt.Sprintf("%s%08x%s", string(tok[:]), len(val), val)
}

func sendToken(sock io.Writer, token string, val int) (err error) {
	var n int
	n, err = io.WriteString(sock, DccEncode(token, val))
	if err != nil {
		log.Println("Failed to send:", err)
		return
	}
	if n != TOKEN_LEN {
		err = fmt.Errorf("Failed to send: expected: %d bytes, actual: %d", TOKEN_LEN, n)
		log.Println(err)
		return
	}
	return
}

func readToken(sock io.Reader, token string) (val int, err error) {
	var (
		buf   [TOKEN_LEN]byte
		n     int
		value int64
	)
	if n, err = io.ReadFull(sock, buf[:]); err != nil {
		if n != TOKEN_LEN {
			log.Printf("readToken: short read: %d bytes of %d", n, TOKEN_LEN)
		} else {
			log.Println("readToken: error:", err)
		}
		return
	}
	t := string(buf[:4])
	if token != t {
		err = fmt.Errorf("wrong token: expected: %s, got: %s", token, t)
		return
	}
	if value, err = strconv.ParseInt(string(buf[4:]), 16, 32); err != nil {
		log.Println(err)
		return
	}
	val = int(value)
	return
}

func sendStringToken(sock io.Writer, token string, val string) (err error) {
	var n int
	encoded := DccEncodeString(token, val)
	n, err = io.WriteString(sock, encoded)
	if err != nil {
		log.Println("Failed to send:", err)
		return
	}
	if n != len(encoded) {
		err = fmt.Errorf("Failed to send: expected %d bytes, actual: %d", len(encoded), n)
		log.Println(err)
		return
	}
	return
}

func (c *DccClient) Request(args []string) (err error) {
	var sz int64
	err = sendToken(c.wsock, "DIST", c.version)
	if err != nil {
		return
	}
	err = sendToken(c.wsock, "ARGC", len(args))
	if err != nil {
		return
	}
	for i, arg := range args {
		err = sendStringToken(c.wsock, "ARGV", arg)
		if err != nil {
			log.Println("Failed to send arg", i)
			return
		}
	}
	err = sendToken(c.wsock, "DOTI", c.dotilen)
	if err != nil {
		return
	}
	sz, err = io.Copy(c.wsock, c.doti)
	if err != nil {
		if sz != int64(c.dotilen) {
			log.Printf("Failed to send DOTI file: partial write: %d bytes of %d", int(sz), c.dotilen)
		} else {
			log.Println("Failed to send DOTI file:", err)
		}
		return
	}
	return
}

func readTokenTo(sock io.Reader, name string, w io.Writer) (err error) {
	var (
		size int
	)
	if size, err = readToken(sock, name); err != nil {
		err = fmt.Errorf("haven't got a valid %s token: %v", name, err)
		return
	}
	if _, err = io.CopyN(w, sock, int64(size)); err != nil {
		err = fmt.Errorf("Failed to receive %s: error: %v", name, err)
		return
	}
	return
}

func (c *DccClient) HandleResponse() (status int, err error) {
	var (
		version int
	)
	if version, err = readToken(c.rsock, "DONE"); err != nil {
		err = fmt.Errorf("haven't got a valid distcc greeting: %v", err)
		return
	}
	if version != c.version {
		err = fmt.Errorf("Unsupported protocol version: %d", version)
		return
	}
	if status, err = readToken(c.rsock, "STAT"); err != nil {
		err = fmt.Errorf("haven't got a valid STAT: %v", err)
		return
	}
	if err = readTokenTo(c.rsock, "SERR", c.stderr); err != nil {
		return
	}
	if err = readTokenTo(c.rsock, "SOUT", c.stdout); err != nil {
		return
	}
	if status == 0 {
		if err = readTokenTo(c.rsock, "DOTO", c.ofile); err != nil {
			log.Println("failed to receive object file")
		}
	}
	return
}

func (c *DccClient) Compile(args []string) (status int, err error) {
	status = -1
	if err = c.Request(args); err != nil {
		log.Println("failed to enqueue compilation", err)
		return
	}
	status, err = c.HandleResponse()
	if err != nil {
		log.Println("failed to process server response", err)
	}
	return
}

func DccCompile(args []string, src string, obj string, where string) (status int, err error) {
	status = -1
	var (
		c       DccClient
		conn    net.Conn
		inf     os.FileInfo
		doti    *os.File
		objfile *os.File
	)

	c.version = 1
	c.stdout = os.Stdout
	c.stderr = os.Stderr

	if doti, err = os.Open(src); err != nil {
		log.Println("failed to open preprocessed source file", src)
		return
	}
	defer doti.Close()
	if inf, err = doti.Stat(); err != nil {
		log.Println("failed to stat preprocessed source file", src)
		return
	}
	c.dotilen = int(inf.Size())
	c.doti = doti

	if objfile, err = os.Create(obj); err != nil {
		log.Println("failed to open object file", obj, "for writing")
		return
	}
	defer objfile.Close()
	c.ofile = objfile

	if conn, err = net.Dial("tcp", where); err != nil {
		log.Println("failed to connect to", where)
		return
	}
	defer conn.Close()
	c.rsock = conn
	c.wsock = conn

	status, err = c.Compile(args)
	return
}
